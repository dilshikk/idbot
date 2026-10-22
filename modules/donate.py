import asyncio
import uuid
import time

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    InlineKeyboardButtonBuy, LabeledPrice
)
from pyrogram.enums import ChatType, ParseMode
from utils import LOGGER
from bot import bot
from config import COMMAND_PREFIX, ADMIN_ID
from database import get_lang, save_payment, get_payment
from utils.i18n import get_translator, load_translations

_invoice_locks: dict[int, asyncio.Lock] = {}


def _get_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _invoice_locks:
        _invoice_locks[user_id] = asyncio.Lock()
    return _invoice_locks[user_id]


def _get_all_donate_variants() -> set:
    variants = set()
    for lang in ("ru", "en", "uz"):
        t = load_translations(lang)
        if "donate_button" in t:
            variants.add(t["donate_button"])
    return variants


def _get_donation_text(_) -> str:
    return (
        f"{_('donate_why_title')}\n"
        f"{_('donate_divider')}\n"
        f"{_('donate_love')}\n"
        f"{_('donate_desc')}\n\n"
        f"{_('donate_choose')}\n\n"
        f"{_('donate_why_contribute')}\n"
        f"{_('donate_motivation')}"
    )


def _get_donation_buttons(amount: int = 5) -> InlineKeyboardMarkup:
    center = InlineKeyboardButton(f"{amount} ⭐️", callback_data=f"gift_{amount}")
    plus = InlineKeyboardButton("+5", callback_data=f"increment_gift_{amount}")
    minus = InlineKeyboardButton("-5", callback_data=f"decrement_gift_{amount}")
    row = [center, plus] if amount == 5 else [minus, center, plus]
    return InlineKeyboardMarkup([row])


@bot.on_message(
    filters.command(["donate", "gift"], prefixes=COMMAND_PREFIX.split("|"))
    | filters.text & filters.create(
        lambda _, __, msg: msg.text and msg.text.strip() in _get_all_donate_variants()
    )
)
async def donate_command(client: Client, message):
    if not message.from_user:
        await message.delete()
        return

    if message.chat.type != ChatType.PRIVATE:
        return  # пропускаем в группах

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))
    LOGGER.info(f"Donation command received from {user_id}")

    try:
        text = message.text.strip()

        if text in _get_all_donate_variants() or len(text.split()) == 1:
            await message.reply_text(
                _get_donation_text(_),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_get_donation_buttons(),
            )
            return

        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) > 0:
            amount = int(parts[1])
            loading = await message.reply_text(
                _("donate_generating").format(amount=amount)
            )
            await _generate_invoice(message.chat.id, user_id, amount, client, loading.id, _)
        else:
            await message.reply_text(_("donate_invalid_input"), parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        LOGGER.error(f"Error in /donate: {e}")
        await message.reply_text(_("donate_system_error"), parse_mode=ParseMode.MARKDOWN)


async def _generate_invoice(chat_id: int, user_id: int, amount: int, client: Client, message_id: int, _):
    lock = _get_lock(user_id)
    if lock.locked():
        await client.send_message(chat_id, _("donate_in_progress"), parse_mode=ParseMode.MARKDOWN)
        return

    back_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton(_("donate_back"), callback_data="show_donate_options")
    ]])

    async with lock:
        try:
            payload = f"contribution_{user_id}_{amount}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            prices = [LabeledPrice(label=_("donate_stars_label").format(amount=amount), amount=amount)]
            pay_btn = InlineKeyboardMarkup([[InlineKeyboardButtonBuy(_("donate_pay_btn"))]])

            await client.send_invoice(
                chat_id=chat_id,
                title=_("donate_invoice_title"),
                description=_("donate_invoice_desc").format(amount=amount),
                payload=payload,
                currency="XTR",
                prices=prices,
                start_parameter="donate-stars",
                reply_markup=pay_btn,
            )
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=_("donate_invoice_generated").format(amount=amount),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_btn,
            )
        except Exception as e:
            LOGGER.error(f"Invoice error for {user_id}: {e}")
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=_("donate_invoice_failed"),
                parse_mode=ParseMode.MARKDOWN,
            )


@bot.on_callback_query(filters.regex(r"^(gift_|increment_gift_|decrement_gift_|show_donate_options|refund_)"))
async def handle_donate_callback(client: Client, callback_query):
    if not callback_query.from_user:
        return

    user_id = callback_query.from_user.id
    _ = get_translator(get_lang(user_id))
    data = callback_query.data
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.id

    try:
        if data.startswith("gift_"):
            amount = int(data.split("_")[1])
            await client.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text=_("donate_generating").format(amount=amount),
            )
            await _generate_invoice(chat_id, user_id, amount, client, message_id, _)
            await callback_query.answer(_("donate_answered"))

        elif data.startswith("increment_gift_"):
            new_amount = int(data.split("_")[2]) + 5
            await callback_query.message.edit_text(
                _get_donation_text(_),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_get_donation_buttons(new_amount),
            )
            await callback_query.answer(_("donate_updated").format(amount=new_amount))

        elif data.startswith("decrement_gift_"):
            new_amount = max(5, int(data.split("_")[2]) - 5)
            await callback_query.message.edit_text(
                _get_donation_text(_),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_get_donation_buttons(new_amount),
            )
            await callback_query.answer(_("donate_updated").format(amount=new_amount))

        elif data == "show_donate_options":
            await callback_query.message.edit_text(
                _get_donation_text(_),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_get_donation_buttons(),
            )
            await callback_query.answer()

        elif data.startswith("refund_"):
            payment_id = data[7:]
            payment = get_payment(payment_id)
            if not payment:
                await callback_query.answer("❌ Payment not found", show_alert=True)
                return
            await client.refund_star_payment(payment["user_id"], payment["charge_id"])
            await callback_query.answer("✅ Refund sent!", show_alert=True)

    except Exception as e:
        LOGGER.error(f"Donation callback error: {e}")
        await callback_query.answer(_("donate_system_error"), show_alert=True)


@bot.on_pre_checkout_query()
async def process_pre_checkout_query(client: Client, pre_checkout_query):
    user_id = pre_checkout_query.from_user.id if pre_checkout_query.from_user else 0
    try:
        await client.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
        LOGGER.info(f"✅ Payment approved: query={pre_checkout_query.id}, user={user_id}")
    except Exception as e:
        LOGGER.error(f"❌ Pre-checkout failed: {e}")
        _ = get_translator(get_lang(user_id))
        await client.answer_pre_checkout_query(
            pre_checkout_query.id, ok=False,
            error_message=_("donate_precheckout_failed"),
        )


@bot.on_message(filters.successful_payment)
async def process_successful_payment(client: Client, message):
    if not message.from_user:
        return

    user = message.from_user
    user_id = user.id
    payment = message.successful_payment
    _ = get_translator(get_lang(user_id))

    try:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        username = f"@{user.username}" if user.username else "N/A"
        amount = payment.total_amount
        charge_id = payment.telegram_payment_charge_id

        payment_id = str(uuid.uuid4())[:16]
        save_payment(payment_id, user_id, full_name, username, amount, charge_id)

        await client.send_message(
            chat_id=message.chat.id,
            text=_("donate_success").format(name=full_name, amount=amount, charge_id=charge_id),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_("donate_copy_tx"), copy_text=charge_id)
            ]]),
        )

        admin_ids = ADMIN_ID if isinstance(ADMIN_ID, (list, tuple)) else [ADMIN_ID]
        refund_btn = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"Refund {amount} ⭐️", callback_data=f"refund_{payment_id}")
        ]])
        for admin_id in admin_ids:
            try:
                await client.send_message(
                    chat_id=admin_id,
                    text=(
                        f"**🤗 New Donation!**\n**━━━━━━━━━━━━━━━**\n"
                        f"**From:** {full_name}\n**Username:** {username}\n"
                        f"**UserID:** `{user_id}`\n**Amount:** {amount} ⭐️\n"
                        f"**Transaction:** `{charge_id}`\n**━━━━━━━━━━━━━━━**"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=refund_btn,
                )
            except Exception as e:
                LOGGER.error(f"Failed to notify admin {admin_id}: {e}")

        LOGGER.info(f"✅ Payment OK: user={user_id}, amount={amount}")

    except Exception as e:
        LOGGER.error(f"❌ Payment processing failed for {user_id}: {e}", exc_info=True)
        await client.send_message(
            chat_id=message.chat.id,
            text=_("donate_payment_declined"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_("donate_contact_support"), url=f"tg://user?id={ADMIN_ID}")
            ]]),
        )
