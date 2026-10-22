from pyrogram import Client, filters
from utils import LOGGER
from utils.ratelimit import throttle
from bot import bot
from database import get_lang
from utils.i18n import get_translator
from modules.helpers import (
    send_entity_info, format_user_response, format_chat_response, format_hidden_sender_response,
)


@bot.on_message(filters.private & filters.forwarded)
async def handle_forwarded_message(client: Client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    lang = get_lang(user_id)
    _ = get_translator(lang)
    LOGGER.info(f"Forwarded message from {user_id}")

    # Пересылка пачкой даёт десятки сообщений сразу: отвечаем не на каждое
    if await throttle(message, lang, action="forward"):
        return

    loading_message = await message.reply_text(_("processing_info"))
    try:
        origin = getattr(message, "forward_origin", None)

        if origin and getattr(origin, "sender_user", None):
            response, full_name = format_user_response(origin.sender_user, _)
            entity_id = origin.sender_user.id
        elif origin and getattr(origin, "chat", None):
            response, full_name = format_chat_response(origin.chat, _)
            entity_id = origin.chat.id
        elif origin and getattr(origin, "sender_chat", None):
            # Сообщение от имени группы или канала (анонимный админ)
            response, full_name = format_chat_response(origin.sender_chat, _)
            entity_id = origin.sender_chat.id
        elif origin and getattr(origin, "sender_user_name", None):
            response, full_name = format_hidden_sender_response(origin.sender_user_name, _)
            entity_id = None
        else:
            response, full_name = format_hidden_sender_response(_("unknown"), _)
            entity_id = None

        await send_entity_info(loading_message, client, entity_id, response, full_name)
        LOGGER.info(f"Sent forwarded info for {entity_id or 'hidden sender'}")

    except Exception as e:
        LOGGER.error(f"Error handling forwarded message for {user_id}: {e}")
        await loading_message.edit_text(_("no_control_over_user"))
