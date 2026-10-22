from datetime import datetime, timezone

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyrogram.enums import ParseMode, ChatType
from utils import LOGGER
from utils.text import md_escape
from miscs.startbtn import get_menu_buttons
from bot import bot
from config import COMMAND_PREFIX, LOG_GROUP_ID
from database import add_user, get_lang, set_lang, user_exists
from utils.i18n import get_translator, LANGUAGES
from modules.callback import _welcome_text
from modules.admin import reply_private_only, send_chat_picker
from modules.language import language_keyboard

# Ссылки вида t.me/bot?start=my сразу открывают нужный раздел
DEEP_LINKS = ("my", "admin")


@bot.on_message(filters.command("start", prefixes=COMMAND_PREFIX.split("|")))
async def start(client: Client, message):
    try:
        if not message.from_user:
            return

        user_id = message.from_user.id
        LOGGER.info(f"--- /start from {user_id} ---")

        if message.chat.type != ChatType.PRIVATE:
            await reply_private_only(message, get_translator(get_lang(user_id)), "start")
            return

        # Новичок сначала выбирает язык, остальное после
        if not user_exists(user_id):
            await message.reply_text(
                get_translator("en")("choose_language"),
                reply_markup=language_keyboard("set_lang_start"),
            )
            LOGGER.info(f"Language selection offered to new user {user_id}")
            return

        param = message.command[1].lower() if len(message.command) > 1 else ""
        if param in DEEP_LINKS:
            await send_chat_picker(message, user_id, param)
            return

        await send_welcome_message(client, message.chat.id, user_id, get_translator(get_lang(user_id)))

    except Exception as e:
        LOGGER.error(f"Error in /start: {e}", exc_info=True)


async def _log_new_user(client: Client, user, lang_code: str) -> None:
    username = f"@{user.username}" if user.username else "N/A"
    try:
        await client.send_message(
            LOG_GROUP_ID,
            (
                "🆕 **#Новый_пользователь**\n"
                "**━━━━━━━━━━━━━━━━━━**\n"
                # Имя задаёт сам пользователь, поэтому экранируем
                f"👤 **Кто:** {md_escape(user.first_name)}\n"
                f"🔗 **Ник:** {md_escape(username)}\n"
                f"🌍 **Язык:** {LANGUAGES[lang_code]}\n"
                f"📅 **Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC\n"
                f"#id{user.id}"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        # Ошибка группы логов не должна мешать пользователю
        LOGGER.warning(f"Could not post new user {user.id} to log group: {e}")


@bot.on_callback_query(filters.regex(r"^set_lang_start:(\w+)$"))
async def set_start_language(client: Client, query: CallbackQuery):
    if not query.from_user or not query.message:
        return

    user = query.from_user
    lang_code = query.data.split(":", 1)[1]
    if lang_code not in LANGUAGES:
        await query.answer("❌ Invalid language!", show_alert=True)
        return

    _ = get_translator(lang_code)
    try:
        # add_user атомарен: при двойном нажатии запись в лог будет только одна
        if add_user(user, lang_code):
            await _log_new_user(client, user, lang_code)
        else:
            set_lang(user.id, lang_code)

        await query.message.edit_text(f"{_('language_set')}\n\n{LANGUAGES[lang_code]}")
        await query.answer()
        LOGGER.info(f"✅ User {user.id} selected language {lang_code}")
        await send_welcome_message(client, query.message.chat.id, user.id, _)

    except Exception as e:
        LOGGER.error(f"Error in language selection: {e}", exc_info=True)
        await query.answer(_("internal_error"), show_alert=True)


async def send_welcome_message(client: Client, chat_id: int, user_id: int, _):
    try:
        await client.send_message(
            chat_id=chat_id,
            text=_welcome_text(_),
            reply_markup=get_menu_buttons(user_id),
        )
        LOGGER.info(f"✅ Welcome message sent to {user_id}")
    except Exception as e:
        LOGGER.error(f"Error sending welcome message: {e}", exc_info=True)
