from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaAnimation
from utils import LOGGER
from bot import bot
from utils.i18n import get_translator
from database import get_lang
from config import COMMAND_PREFIX
from modules.helpers import format_user_response, format_chat_response, get_profile_photo_file_id


async def _send_entity_info(loading_message, bot, entity_id: int, response: str, full_name: str, _):
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton(text=full_name, copy_text=str(entity_id))]])
    try:
        photo_file_id, is_animated = await get_profile_photo_file_id(bot, entity_id)
        if photo_file_id:
            media_cls = InputMediaAnimation if is_animated else InputMediaPhoto
            await loading_message.edit_media(
                media=media_cls(media=photo_file_id, caption=response),
                reply_markup=buttons,
            )
        else:
            await loading_message.edit_text(response, reply_markup=buttons)
    except Exception as e:
        LOGGER.error(f"Error sending photo for {entity_id}: {e}")
        await loading_message.edit_text(response, reply_markup=buttons)


@bot.on_message(filters.command(["info", "id"], prefixes=COMMAND_PREFIX.split("|")))
async def info_command(bot: Client, message):
    if not message.from_user:
        await message.delete()
        return

    if message.chat.type != ChatType.PRIVATE:
        return  # пропускаем в группах

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))

    LOGGER.info(f"/info command received from {user_id}")
    loading_message = await message.reply_text(_("processing_info"))
    command_parts = message.text.split()

    if len(command_parts) == 1 or command_parts[1].lower() == "me":
        try:
            user = message.from_user
            response, full_name = format_user_response(user, False, None, _)
            await _send_entity_info(loading_message, bot, user.id, response, full_name, _)
        except Exception as e:
            LOGGER.error(f"Error in /info me for {user_id}: {e}")
            await loading_message.edit_text(_("no_control_over_user"))
        return

    username = (
        command_parts[1]
        .strip("@")
        .replace("https://", "")
        .replace("http://", "")
        .replace("t.me/", "")
        .replace("/", "")
        .replace(":", "")
    )

    try:
        chat = await bot.get_chat(username)
        entity_id = chat.id
        chat_type = chat.type
        is_group = chat_type in (ChatType.GROUP, ChatType.SUPERGROUP)

        if chat_type in (ChatType.PRIVATE, ChatType.BOT):
            entity = await bot.get_users(entity_id)
            response, full_name = format_user_response(entity, is_group, chat if is_group else None, _)
        else:
            response, full_name = format_chat_response(chat, _)

        await _send_entity_info(loading_message, bot, entity_id, response, full_name, _)

    except Exception as e:
        LOGGER.error(f"Error fetching info for {username}: {e}")
        await loading_message.edit_text(_("no_control_over_user"))
