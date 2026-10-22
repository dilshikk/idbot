from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaAnimation
from utils import LOGGER
from bot import bot
from config import COMMAND_PREFIX
from database import get_lang
from utils.i18n import get_translator
from modules.helpers import format_user_response, get_profile_photo_file_id


@bot.on_message(filters.command("me", prefixes=COMMAND_PREFIX.split("|")))
async def me_command(bot: Client, message):
    if not message.from_user:
        await message.delete()
        return

    if message.chat.type != ChatType.PRIVATE:
        return  # пропускаем в группах

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))

    LOGGER.info(f"/me command received from {user_id}")
    loading_message = await message.reply_text(_("processing_info"))

    try:
        user = message.from_user
        response, full_name = format_user_response(user, False, None, _)
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text=full_name, copy_text=str(user.id))]]
        )

        try:
            photo_file_id, is_animated = await get_profile_photo_file_id(bot, user.id)
            if photo_file_id:
                media_cls = InputMediaAnimation if is_animated else InputMediaPhoto
                await loading_message.edit_media(
                    media=media_cls(media=photo_file_id, caption=response),
                    reply_markup=buttons,
                )
                LOGGER.info(f"Sent user info with photo for {user.id}")
            else:
                await loading_message.edit_text(response, reply_markup=buttons)
                LOGGER.info(f"Sent user info without photo for {user.id}")

        except Exception as e:
            LOGGER.error(f"Error sending photo for {user.id}: {e}")
            await loading_message.edit_text(response, reply_markup=buttons)

    except Exception as e:
        LOGGER.error(f"Error processing /me for {user_id}: {e}")
        await loading_message.edit_text(_("no_control_over_user"))
