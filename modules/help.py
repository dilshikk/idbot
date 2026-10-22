from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import LOGGER
from bot import bot
from config import COMMAND_PREFIX
from database import get_lang
from utils.i18n import get_translator
from modules.callback import button_filter

HELP_SECTIONS = (
    "help_forward", "help_getme", "help_sharedchat",
    "help_admins", "help_ownchats", "help_username",
)


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


@bot.on_message(
    filters.private
    & (filters.command("help", prefixes=COMMAND_PREFIX.split("|")) | button_filter("help_button"))
)
async def help_command(client: Client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    lang = get_lang(user_id)
    _ = get_translator(lang)
    LOGGER.info(f"/help called by {user_id} (lang={lang})")
    try:
        await message.reply_text(_("help_main"), reply_markup=get_help_keyboard(lang))
    except Exception as e:
        LOGGER.error(f"Error in /help: {e}", exc_info=True)


@bot.on_callback_query(filters.regex(rf"^({'|'.join(HELP_SECTIONS)}|help_close|main_menu)$"))
async def handle_help_callback(client: Client, callback_query):
    if not callback_query.from_user or not callback_query.message:
        return

    user_id = callback_query.from_user.id
    lang = get_lang(user_id)
    _ = get_translator(lang)
    data = callback_query.data
    LOGGER.info(f"[HELP] data={data}, user={user_id}")

    try:
        if data == "help_close":
            await callback_query.message.delete()
        elif data == "main_menu":
            await callback_query.message.edit_text(_("help_main"), reply_markup=get_help_keyboard(lang))
        else:
            await callback_query.message.edit_text(_(data), reply_markup=get_back_button(lang))
    except Exception as e:
        LOGGER.error(f"Error in help callback: {e}", exc_info=True)
    finally:
        # Без ответа у пользователя бесконечно крутятся «часики» на кнопке
        try:
            await callback_query.answer()
        except Exception:
            pass
