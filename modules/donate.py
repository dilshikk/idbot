import asyncio
import uuid
import time

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    InlineKeyboardButtonBuy, LabeledPrice
)
from pyrogram.enums import ParseMode
from utils import LOGGER
from utils.text import md_escape
from utils.ratelimit import is_limited
from bot import bot
from config import COMMAND_PREFIX, ADMIN_ID
from database import get_lang, save_payment, get_payment, claim_refund, release_refund
from utils.i18n import get_translator
from modules.callback import button_filter
from modules.helpers import display_name

CURRENCY = "XTR"
PAYLOAD_PREFIX = "contribution"
MIN_AMOUNT = 1
MAX_AMOUNT = 100_000  # верхний предел Telegram Stars на один счёт
STEP = 5
INVOICE_INTERVAL = 3.0  # не чаще одного счёта в 3 секунды

_invoice_locks: dict[int, asyncio.Lock] = {}


def _admin_ids() -> list[int]:
    """ADMIN_ID в конфиге может быть одним числом или списком."""
    return list(ADMIN_ID) if isinstance(ADMIN_ID, (list, tuple, set)) else [ADMIN_ID]


def _is_admin(user_id: int) -> bool:
    return user_id in _admin_ids()


def _is_valid_amount(amount: int) -> bool:
    return MIN_AMOUNT <= amount <= MAX_AMOUNT


def _parse_amount(raw: str) -> int | None:
    """Сумма из callback_data. Кнопку можно подделать, поэтому проверяем всегда."""
    return int(raw) if raw.isdigit() and _is_valid_amount(int(raw)) else None


def _build_payload(user_id: int, amount: int) -> str:
    return f"{PAYLOAD_PREFIX}_{user_id}_{amount}_{int(time.time())}_{uuid.uuid4().hex[:8]}"


def _validate_payment(payload, user_id: int, amount: int, currency: str) -> str | None:
    """Проверяет, что оплачивается именно наш счёт.
    Возвращает причину отказа или None, если всё в порядке."""
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="ignore")
    if currency != CURRENCY:
        return f"wrong currency {currency}"

    parts = (payload or "").split("_")
    if len(parts) != 5 or parts[0] != PAYLOAD_PREFIX:
        return "unknown payload format"

    _, payload_user, payload_amount, _ts, _rnd = parts
    if not (payload_user.isdigit() and payload_amount.isdigit()):
        return "malformed payload"
    if int(payload_user) != user_id:
        return f"payload user {payload_user} != payer {user_id}"
    if int(payload_amount) != amount:
        return f"payload amount {payload_amount} != paid {amount}"
    if not _is_valid_amount(amount):
        return f"amount out of range: {amount}"
    return None


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


def _get_donation_buttons(amount: int = STEP) -> InlineKeyboardMarkup:
    center = InlineKeyboardButton(f"{amount} ⭐️", callback_data=f"gift_{amount}")
    plus = InlineKeyboardButton(f"+{STEP}", callback_data=f"increment_gift_{amount}")
    minus = InlineKeyboardButton(f"-{STEP}", callback_data=f"decrement_gift_{amount}")
    row = [center, plus] if amount <= STEP else [minus, center, plus]
    return InlineKeyboardMarkup([row])


@bot.on_message(
    filters.private
    & (filters.command(["donate", "gift"], prefixes=COMMAND_PREFIX.split("|")) | button_filter("donate_button"))
)
async def donate_command(client: Client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))
    LOGGER.info(f"Donation command received from {user_id}")

    try:
        args = (message.command or [])[1:]  # у нажатой кнопки command = None
        if not args:
            await message.reply_text(
                _get_donation_text(_),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_get_donation_buttons(),
            )
            return

        amount = _parse_amount(args[0]) if len(args) == 1 else None
        if amount is None:
            await message.reply_text(_("donate_invalid_input"), parse_mode=ParseMode.MARKDOWN)
            return

        loading = await message.reply_text(_("donate_generating").format(amount=amount))
        await _generate_invoice(message.chat.id, user_id, amount, client, loading.id, _)

    except Exception as e:
        LOGGER.error(f"Error in /donate: {e}")
        await message.reply_text(_("donate_system_error"), parse_mode=ParseMode.MARKDOWN)


async def _generate_invoice(chat_id: int, user_id: int, amount: int, client: Client, message_id: int, _):
    lock = _invoice_locks.setdefault(user_id, asyncio.Lock())
    if lock.locked() or is_limited(user_id, "invoice", INVOICE_INTERVAL):
        await client.send_message(chat_id, _("donate_in_progress"), parse_mode=ParseMode.MARKDOWN)
        return

    back_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton(_("donate_back"), callback_data="show_donate_options")
    ]])

    try:
        async with lock:
            try:
                payload = _build_payload(user_id, amount)
                prices = [LabeledPrice(label=_("donate_stars_label").format(amount=amount), amount=amount)]
                pay_btn = InlineKeyboardMarkup([[InlineKeyboardButtonBuy(_("donate_pay_btn"))]])

                await client.send_invoice(
                    chat_id=chat_id,
                    title=_("donate_invoice_title"),
                    description=_("donate_invoice_desc").format(amount=amount),
                    payload=payload,
                    currency=CURRENCY,
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
    finally:
        # Не держим замок в памяти вечно для каждого, кто хоть раз донатил
        if not lock.locked():
            _invoice_locks.pop(user_id, None)


async def _show_amount(callback_query, _, amount: int) -> None:
    await callback_query.message.edit_text(
        _get_donation_text(_),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_get_donation_buttons(amount),
    )
    await callback_query.answer(_("donate_updated").format(amount=amount))


async def _handle_refund(client: Client, callback_query, user_id: int, payment_id: str) -> None:
    # Возврат может сделать только админ: callback_data можно подделать,
    # поэтому проверяем того, кто нажал кнопку, а не то, где она показана.
    if not _is_admin(user_id):
        LOGGER.warning(f"⛔ Unauthorized refund attempt by {user_id}: {payment_id}")
        await callback_query.answer("⛔ Access denied", show_alert=True)
        return

    payment = get_payment(payment_id)
    if not payment:
        await callback_query.answer("❌ Payment not found", show_alert=True)
        return

    # Отметка ставится до запроса в Telegram: двойное нажатие не вернёт деньги дважды
    if not claim_refund(payment_id):
        await callback_query.answer("ℹ️ Already refunded", show_alert=True)
        return

    try:
        await client.refund_star_payment(payment["user_id"], payment["charge_id"])
    except Exception:
        release_refund(payment_id)
        raise

    LOGGER.info(f"↩️ Refund by admin {user_id}: payment={payment_id}, user={payment['user_id']}")
    await callback_query.answer("✅ Refund sent!", show_alert=True)
    try:
        await callback_query.message.edit_reply_markup(None)
    except Exception:
        pass


@bot.on_callback_query(filters.regex(r"^(gift_|increment_gift_|decrement_gift_|show_donate_options$|refund_)"))
async def handle_donate_callback(client: Client, callback_query):
    if not callback_query.from_user or not callback_query.message:
        return

    user_id = callback_query.from_user.id
    _ = get_translator(get_lang(user_id))
    data = callback_query.data
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.id

    try:
        if data.startswith("refund_"):
            await _handle_refund(client, callback_query, user_id, data[len("refund_"):])
            return

        if data == "show_donate_options":
            await _show_amount(callback_query, _, STEP)
            return

        amount = _parse_amount(data.rsplit("_", 1)[-1])
        if amount is None:
            await callback_query.answer(_("donate_invalid_input"), show_alert=True)
            return

        if data.startswith("increment_gift_"):
            await _show_amount(callback_query, _, min(MAX_AMOUNT, amount + STEP))
        elif data.startswith("decrement_gift_"):
            await _show_amount(callback_query, _, max(STEP, amount - STEP))
        else:  # gift_
            await client.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text=_("donate_generating").format(amount=amount),
            )
            await _generate_invoice(chat_id, user_id, amount, client, message_id, _)
            await callback_query.answer(_("donate_answered"))

    except Exception as e:
        LOGGER.error(f"Donation callback error: {e}")
        try:
            await callback_query.answer(_("donate_system_error"), show_alert=True)
        except Exception:
            pass


@bot.on_pre_checkout_query()
async def process_pre_checkout_query(client: Client, pre_checkout_query):
    user_id = pre_checkout_query.from_user.id if pre_checkout_query.from_user else 0
    _ = get_translator(get_lang(user_id))

    # Сверяем счёт с плательщиком, суммой и валютой
    reason = _validate_payment(
        pre_checkout_query.invoice_payload,
        user_id,
        pre_checkout_query.total_amount,
        pre_checkout_query.currency,
    )

    try:
        if reason:
            LOGGER.warning(f"⛔ Payment rejected: query={pre_checkout_query.id}, user={user_id}, reason={reason}")
            await client.answer_pre_checkout_query(
                pre_checkout_query.id, ok=False,
                error_message=_("donate_precheckout_failed"),
            )
            return

        await client.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
        LOGGER.info(f"✅ Payment approved: query={pre_checkout_query.id}, user={user_id}")
    except Exception as e:
        LOGGER.error(f"❌ Pre-checkout answer failed: {e}")


async def _notify_admins(client: Client, text: str, markup: InlineKeyboardMarkup | None) -> None:
    for admin_id in _admin_ids():
        try:
            await client.send_message(chat_id=admin_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        except Exception as e:
            LOGGER.error(f"Failed to notify admin {admin_id}: {e}")


@bot.on_message(filters.successful_payment)
async def process_successful_payment(client: Client, message):
    if not message.from_user:
        return

    user = message.from_user
    user_id = user.id
    payment = message.successful_payment
    _ = get_translator(get_lang(user_id))

    try:
        full_name = display_name(user.first_name, user.last_name, str(user_id))
        username = f"@{user.username}" if user.username else "N/A"
        amount = payment.total_amount
        charge_id = payment.telegram_payment_charge_id

        # Деньги уже списаны, поэтому платёж сохраняем в любом случае,
        # а о несовпадении сообщаем админу, чтобы он мог сделать возврат.
        mismatch = _validate_payment(
            getattr(payment, "invoice_payload", ""), user_id, amount, payment.currency
        )
        if mismatch:
            LOGGER.error(f"⚠️ Successful payment mismatch: user={user_id}, charge={charge_id}, reason={mismatch}")

        payment_id = uuid.uuid4().hex[:16]
        saved = save_payment(payment_id, user_id, full_name, username, amount, charge_id)

        await client.send_message(
            chat_id=message.chat.id,
            text=_("donate_success").format(name=md_escape(full_name), amount=amount, charge_id=charge_id),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_("donate_copy_tx"), copy_text=charge_id)
            ]]),
        )

        # Кнопка возврата только если платёж реально записан в базу
        refund_btn = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"Refund {amount} ⭐️", callback_data=f"refund_{payment_id}")
        ]]) if saved else None
        warning = f"\n⚠️ **Check:** {md_escape(mismatch)}" if mismatch else ""
        not_saved = "\n⚠️ **Not saved to DB, refund manually**" if not saved else ""
        await _notify_admins(
            client,
            (
                f"**🤗 New Donation!**\n**━━━━━━━━━━━━━━━**\n"
                # Имя и ник задаёт сам плательщик: экранируем, чтобы не подменили ссылки
                f"**From:** {md_escape(full_name)}\n**Username:** {md_escape(username)}\n"
                f"**UserID:** `{user_id}`\n**Amount:** {amount} ⭐️\n"
                f"**Transaction:** `{md_escape(charge_id)}`{warning}{not_saved}\n**━━━━━━━━━━━━━━━**"
            ),
            refund_btn,
        )
        LOGGER.info(f"✅ Payment OK: user={user_id}, amount={amount}")

    except Exception as e:
        LOGGER.error(f"❌ Payment processing failed for {user_id}: {e}", exc_info=True)
        await client.send_message(
            chat_id=message.chat.id,
            text=_("donate_payment_declined"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_("donate_contact_support"), url=f"tg://user?id={_admin_ids()[0]}")
            ]]),
        )
