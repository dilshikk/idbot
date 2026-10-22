from pyrogram import Client, filters
from utils import LOGGER
from utils.ratelimit import throttle
from bot import bot
from database import get_lang
from utils.i18n import get_translator
from modules.helpers import describe_peer, send_entity_info

# Только настоящий формат юзернейма. Раньше подходил любой текст после @,
# включая пробелы и спецсимволы, и всё это уходило запросом в Telegram.
USERNAME_PATTERN = r"^@[A-Za-z][A-Za-z0-9_]{3,31}$"


@bot.on_message(filters.private & filters.regex(USERNAME_PATTERN))
async def username_command(client: Client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    lang = get_lang(user_id)
    _ = get_translator(lang)
    LOGGER.info(f"Username message received from user {user_id}")

    if await throttle(message, lang):
        return

    loading_message = await message.reply_text(_("processing_info"))
    username = message.text.strip().lstrip("@")

    try:
        chat = await client.get_chat(username)
        response, full_name = await describe_peer(client, chat, _)
        await send_entity_info(loading_message, client, chat.id, response, full_name)
    except Exception as e:
        LOGGER.error(f"Error fetching chat @{username} for user {user_id}: {e}")
        await loading_message.edit_text(_("no_control_over_user"))
