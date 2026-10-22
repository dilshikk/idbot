from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaAnimation
from utils import LOGGER
from bot import bot
from database import get_lang
from utils.i18n import get_translator
from modules.helpers import get_profile_photo_file_id, format_user_response, format_chat_response, format_hidden_sender_response


@bot.on_message(filters.private & filters.forwarded)
async def handle_forwarded_message(bot: Client, message):
    if not message.from_user:
        await message.delete()
        return

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))

    LOGGER.info(f"Forwarded message from {user_id}")
    loading_message = await message.reply_text(_("processing_info"))

    try:
        origin = getattr(message, "forward_origin", None)

        if origin and getattr(origin, "sender_user", None):
            user = origin.sender_user
            response, full_name = format_user_response(user, False, None, _)
            entity_id = user.id

        elif origin and getattr(origin, "chat", None):
            chat = origin.chat
            response, full_name = format_chat_response(chat, _)
            entity_id = chat.id

        elif origin and getattr(origin, "sender_user_name", None):
            response, full_name = format_hidden_sender_response(origin.sender_user_name, _)
            entity_id = None

        else:
            response, full_name = format_hidden_sender_response(_("unknown"), _)
            entity_id = None

        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                text=full_name,
                copy_text=str(entity_id) if entity_id else full_name,
            )
        ]])

        try:
            photo_file_id, is_animated = (
                await get_profile_photo_file_id(bot, entity_id)
                if entity_id else (None, False)
            )
            if photo_file_id:
                media_cls = InputMediaAnimation if is_animated else InputMediaPhoto
                await loading_message.edit_media(
                    media=media_cls(media=photo_file_id, caption=response),
                    reply_markup=buttons,
                )
            else:
                await loading_message.edit_text(response, reply_markup=buttons)

            LOGGER.info(f"Sent forwarded info for {entity_id or 'hidden sender'}")

        except Exception as e:
            LOGGER.error(f"Error sending photo for {entity_id}: {e}")
            await loading_message.edit_text(response, reply_markup=buttons)

    except Exception as e:
        LOGGER.error(f"Error handling forwarded message for {user_id}: {e}")
        await loading_message.edit_text(_("no_control_over_user"))
