from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import LOGGER
from bot import bot
from config import COMMAND_PREFIX
from database import get_lang
from utils.i18n import get_translator
from modules.callback import _get_all_variants


def get_help_keyboard(lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(_("help_btn_forward"), callback_data="help_forward"),
            InlineKeyboardButton(_("help_btn_getme"), callback_data="help_getme"),
        ],
        [
            InlineKeyboardButton(_("help_btn_sharedchat"), callback_data="help_sharedchat"),
            InlineKeyboardButton(_("help_btn_admins"), callback_data="help_admins"),
        ],
        [
            InlineKeyboardButton(_("help_btn_ownchats"), callback_data="help_ownchats"),
            InlineKeyboardButton(_("help_btn_username"), callback_data="help_username"),
        ],
        [InlineKeyboardButton(_("help_btn_close"), callback_data="help_close")],
        [InlineKeyboardButton(_("help_btn_updates"), url="https://t.me/ibots_dev")],
    ])


def get_back_button(lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(_("help_back"), callback_data="main_menu")
    ]])


def get_help_texts(_) -> dict:
    return {
        "main":          _("help_main"),
        "help_forward":  _("help_forward"),
        "help_getme":    _("help_getme"),
        "help_sharedchat": _("help_sharedchat"),
        "help_admins":   _("help_admins"),
        "help_ownchats": _("help_ownchats"),
        "help_username": _("help_username"),
    }


@bot.on_message(
    filters.command("help", prefixes=COMMAND_PREFIX.split("|"))
    | filters.text & filters.create(
        lambda _, __, msg: msg.text and msg.text.strip() in _get_all_variants("help_button")
    )
)
async def help_command(bot: Client, message):
    if not message.from_user:
        await message.delete()
        return

    if message.chat.type != ChatType.PRIVATE:
        return  # пропускаем в группах

    user_id = message.from_user.id
    lang = get_lang(user_id)
    _ = get_translator(lang)

    LOGGER.info(f"/help called by {user_id} (lang={lang})")
    try:
        await message.reply_text(
            get_help_texts(_)["main"],
            reply_markup=get_help_keyboard(lang),
        )
    except Exception as e:
        LOGGER.error(f"Error in /help: {e}", exc_info=True)


@bot.on_callback_query(filters.regex(
    r"^(help_forward|help_getme|help_sharedchat|help_admins|help_ownchats|help_username|help_close|main_menu)$"
))
async def handle_help_callback(bot: Client, callback_query):
    if not callback_query.from_user:
        return

    user_id = callback_query.from_user.id
    lang = get_lang(user_id)
    _ = get_translator(lang)
    texts = get_help_texts(_)

    data = callback_query.data
    LOGGER.info(f"[HELP] data={data}, user={user_id}")

    try:
        if data == "help_close":
            await callback_query.message.delete()
            return

        if data == "main_menu":
            await callback_query.message.edit_text(
                texts["main"],
                reply_markup=get_help_keyboard(lang),
            )
            return

        await callback_query.message.edit_text(
            texts.get(data, _("help_coming_soon")),
            reply_markup=get_back_button(lang),
        )

    except Exception as e:
        LOGGER.error(f"Error in help callback: {e}", exc_info=True)
