from pyrogram import Client, filters
from utils import LOGGER
from bot import bot
from config import COMMAND_PREFIX
from database import get_lang
from utils.i18n import get_translator
from modules.helpers import format_user_response, send_entity_info


async def send_own_profile(client: Client, message, _) -> None:
    """Карточка самого пользователя. Используется в /me и в /info без аргументов."""
    loading_message = await message.reply_text(_("processing_info"))
    try:
        user = message.from_user
        response, full_name = format_user_response(user, _)
        await send_entity_info(loading_message, client, user.id, response, full_name)
    except Exception as e:
        LOGGER.error(f"Error processing own profile for {message.from_user.id}: {e}")
        await loading_message.edit_text(_("no_control_over_user"))


@bot.on_message(filters.private & filters.command("me", prefixes=COMMAND_PREFIX.split("|")))
async def me_command(client: Client, message):
    if not message.from_user:
        return
    LOGGER.info(f"/me command received from {message.from_user.id}")
    await send_own_profile(client, message, get_translator(get_lang(message.from_user.id)))
