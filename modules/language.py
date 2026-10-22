from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import bot
from utils import LOGGER
from database import get_lang, set_lang, add_user
from config import COMMAND_PREFIX
from miscs.startbtn import get_menu_buttons
from utils.i18n import get_translator, LANGUAGES
from modules.callback import button_filter


def language_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text=name, callback_data=f"{prefix}:{code}")]
        for code, name in LANGUAGES.items()
    ])


@bot.on_message(
    filters.command(["language", "lang"], prefixes=COMMAND_PREFIX.split("|"))
    | (filters.private & button_filter("language_button"))
)
async def choose_language(client: Client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))
    await message.reply_text(_("choose_language"), reply_markup=language_keyboard("set_lang"))
    LOGGER.info(f"Language menu opened for user {user_id}")


@bot.on_callback_query(filters.regex(r"^set_lang:(\w+)$"))
async def set_user_language(client: Client, query):
    if not query.from_user or not query.message:
        return

    user_id = query.from_user.id
    lang_code = query.data.split(":", 1)[1]

    if lang_code not in LANGUAGES:
        current = get_translator(get_lang(user_id))
        await query.answer(current("invalid_language"), show_alert=True)
        return

    _ = get_translator(lang_code)
    try:
        # Если пользователя ещё нет в базе, раньше язык молча не сохранялся
        if not set_lang(user_id, lang_code):
            add_user(query.from_user, lang_code)

        await query.message.edit_text(f"**{_('language_set')}**\n\n**{LANGUAGES[lang_code]}**")
        await client.send_message(
            chat_id=user_id,
            text=f"**{_('welcome_title')}**\n\n{_('fetch_cta')}",
            reply_markup=get_menu_buttons(user_id),
        )
        await query.answer()
        LOGGER.info(f"✅ User {user_id} changed language to {lang_code}")
    except Exception as e:
        LOGGER.error(f"Error changing language for {user_id}: {e}", exc_info=True)
        await query.answer(_("internal_error"), show_alert=True)
