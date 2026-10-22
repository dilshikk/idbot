from pyrogram import Client, filters
from utils import LOGGER
from bot import bot
from config import COMMAND_PREFIX
from modules.admin import send_chat_picker


@bot.on_message(filters.command("my", prefixes=COMMAND_PREFIX.split("|")))
async def my_command(client: Client, message):
    if not message.from_user:
        return
    LOGGER.info(f"/my command received from {message.from_user.id} in {message.chat.type}")
    await send_chat_picker(message, message.from_user.id, "my")
