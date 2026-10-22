from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaAnimation
from pyrogram.enums import ChatType
from utils import LOGGER
from bot import bot
from database import get_lang
from utils.i18n import get_translator
from modules.helpers import get_profile_photo_file_id, format_user_response_resolve, format_chat_response_resolve


@bot.on_message(filters.private & filters.regex(r"^@.{4,32}$"))
async def username_command(bot: Client, message):
    if not message.from_user:
        await message.delete()
        return

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))

    LOGGER.info(f"Username message received from user {user_id}")
    loading_message = await message.reply_text(_("processing_info"))
    username = message.text.strip()

    try:
        chat = await bot.get_chat(username)
        entity_id = chat.id
        chat_type = chat.type

        if chat_type in (ChatType.PRIVATE, ChatType.BOT):
            entity = await bot.get_users(entity_id)
            response, full_name = format_user_response_resolve(entity, False, None, _)
        else:
            response, full_name = format_chat_response_resolve(chat, _)

        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text=full_name, copy_text=str(entity_id))]]
        )

        try:
            photo_file_id, is_animated = await get_profile_photo_file_id(bot, entity_id)
            if photo_file_id:
                media_cls = InputMediaAnimation if is_animated else InputMediaPhoto
                await loading_message.edit_media(
                    media=media_cls(media=photo_file_id, caption=response),
                    reply_markup=buttons,
                )
                LOGGER.info(f"Sent {chat_type.name.lower()} info with photo for {entity_id}")
            else:
                await loading_message.edit_text(response, reply_markup=buttons)
                LOGGER.info(f"Sent {chat_type.name.lower()} info without photo for {entity_id}")

        except Exception as e:
            LOGGER.error(f"Error sending photo for {entity_id}: {e}")
            await loading_message.edit_text(response, reply_markup=buttons)

    except Exception as e:
        LOGGER.error(f"Error fetching chat {username} for user {user_id}: {e}")
        await loading_message.edit_text(_("no_control_over_user"))
