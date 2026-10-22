from pyrogram import Client, filters
from pyrogram.types import BotCommand, BotCommandScopeAllPrivateChats
from bot import bot
from utils import LOGGER
from config import COMMAND_PREFIX
from database import get_lang
from utils.i18n import get_translator, LANGUAGES
from miscs.startbtn import get_settings_buttons
from modules.callback import button_filter

# Команды в синей кнопке «Меню» Telegram (слева от поля ввода)
BOT_COMMANDS = ("start", "help", "me", "language", "donate")
FALLBACK_LANG = "en"  # для пользователей с другими языками Telegram


@bot.on_message(
    filters.private
    & (filters.command("settings", prefixes=COMMAND_PREFIX.split("|")) | button_filter("settings_button"))
)
async def settings_menu(client: Client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))
    LOGGER.info(f"Settings menu opened by {user_id}")
    await message.reply_text(_("settings_title"), reply_markup=get_settings_buttons(user_id))


async def setup_bot_commands(client: Client) -> None:
    """Регистрирует список команд на каждом языке.
    Telegram сам покажет пользователю список на языке его приложения."""
    scope = BotCommandScopeAllPrivateChats()
    for lang in LANGUAGES:
        _ = get_translator(lang)
        commands = [BotCommand(cmd, _(f"cmd_{cmd}")) for cmd in BOT_COMMANDS]
        try:
            await client.set_bot_commands(commands, scope=scope, language_code=lang)
            if lang == FALLBACK_LANG:
                await client.set_bot_commands(commands, scope=scope)
        except Exception as e:
            LOGGER.error(f"Failed to set bot commands for lang={lang}: {e}")
    LOGGER.info("✅ Bot commands menu registered")
