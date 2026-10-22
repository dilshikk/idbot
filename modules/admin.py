from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType
from utils import LOGGER
from database import get_lang
from utils.i18n import get_translator
from miscs.adbtn import get_admin_buttons
from bot import bot, get_bot_username
from config import COMMAND_PREFIX
from modules.callback import _chat_list_text


@bot.on_message(filters.command("admin", prefixes=COMMAND_PREFIX.split("|")))
async def admin_command(bot: Client, message):
    if not message.from_user:
        await message.delete()
        return

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))
    LOGGER.info(f"/admin command from {user_id} in {message.chat.type}")

    if message.chat.type != ChatType.PRIVATE:
        bot_username = await get_bot_username()
        await message.reply_text(
            _("admin_private_only"),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_("admin_open_chat"), url=f"https://t.me/{bot_username}")
            ]])
        )
        return

    await message.reply_text(_chat_list_text(_), reply_markup=get_admin_buttons(user_id))
