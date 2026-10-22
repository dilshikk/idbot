from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.enums import ChatType
from utils import LOGGER
from miscs.startbtn import get_menu_buttons
from bot import bot
from config import COMMAND_PREFIX, LOG_GROUP_ID
from database import add_user, get_lang, set_lang, user_exists
from utils.i18n import get_translator, LANGUAGES
from datetime import datetime


@bot.on_message(filters.command("start", prefixes=COMMAND_PREFIX.split("|")))
async def start(bot: Client, message):
    try:
        if not message.from_user:
            await message.delete()
            return

        user_id = message.from_user.id
        username = message.from_user.username or "N/A"
        LOGGER.info(f"--- /start from {user_id} (@{username}) ---")

        # get_lang всегда возвращает язык (по умолчанию "ru"),
        # поэтому новичка определяем только по наличию в базе
        if not user_exists(user_id):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(name, callback_data=f"set_lang_start:{code}")]
                for code, name in LANGUAGES.items()
            ])
            _ = get_translator("en")
            await message.reply_text(
                _("choose_language"),
                reply_markup=keyboard,
            )
            LOGGER.info(f"Language selection offered to new user {user_id}")
            return

        current_lang = get_lang(user_id)
        _ = get_translator(current_lang)
        await send_welcome_message(bot, message.chat.id, user_id, _, current_lang)

    except Exception as e:
        LOGGER.error(f"Error in /start: {e}", exc_info=True)


@bot.on_callback_query(filters.regex(r"^set_lang_start:(\w+)$"))
async def set_start_language(bot: Client, query: CallbackQuery):
    try:
        if not query.from_user:
            return

        user = query.from_user
        user_id = user.id
        username = f"@{user.username}" if user.username else "N/A"
        lang_code = query.data.split(":")[1]

        if lang_code not in LANGUAGES:
            await query.answer("❌ Invalid language!", show_alert=True)
            return

        if not user_exists(user_id):
            add_user(user)
            LOGGER.info(f"🆕 User {user_id} added to database")
            await bot.send_message(
                LOG_GROUP_ID,
                (
                    "🆕 **#Новый_пользователь**\n"
                    "**━━━━━━━━━━━━━━━━━━**\n"
                    f"👤 **Кто:** {user.first_name}\n"
                    f"🔗 **Ник:** {username}\n"
                    f"🌍 **Язык:** {LANGUAGES[lang_code]}\n"
                    f"📅 **Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    f"#id{user_id}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

        set_lang(user_id, lang_code)
        _ = get_translator(lang_code)

        await query.message.edit_text(
            f"{_('language_set')}\n\n{LANGUAGES[lang_code]}"
        )
        LOGGER.info(f"✅ User {user_id} selected language {lang_code}")
        await send_welcome_message(bot, query.message.chat.id, user_id, _, lang_code)

    except Exception as e:
        LOGGER.error(f"Error in language selection: {e}", exc_info=True)
        await query.answer("⚠️ Internal error!", show_alert=True)


async def send_welcome_message(bot: Client, chat_id: int, user_id: int, _, lang_code: str):
    try:
        chat = await bot.get_chat(chat_id)
        if chat.type != ChatType.PRIVATE:
            return  # пропускаем в группах

        text = (
            f"**{_('welcome_title')}**\n\n"
            f"**{_('welcome_how_to')}**\n"
            f"{_('welcome_step1')}\n"
            f"{_('welcome_step2')}\n\n"
            f"**{_('features_title')}**\n"
            f"{_('features_list')}\n\n"
            f"**{_('fetch_cta')}**"
        )
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=get_menu_buttons(user_id),
        )
        LOGGER.info(f"✅ Welcome message sent to {user_id} (lang={lang_code})")

    except Exception as e:
        LOGGER.error(f"Error sending welcome message: {e}", exc_info=True)
