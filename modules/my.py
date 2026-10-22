from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType
from utils import LOGGER
from miscs.mybtn import get_my_buttons
from bot import bot, get_bot_username
from config import COMMAND_PREFIX
from database import get_lang
from utils.i18n import get_translator
from modules.callback import _chat_list_text

@bot.on_message(filters.command("my", prefixes=COMMAND_PREFIX.split("|")))
async def my_command(bot: Client, message):
    if not message.from_user:
        await message.delete()
        return

    user_id = message.from_user.id
    lang = get_lang(user_id)
    _ = get_translator(lang)

    LOGGER.info(f"/my command received from {user_id} in {message.chat.type} (lang={lang})")

    if message.chat.type != ChatType.PRIVATE:
        bot_username = await get_bot_username()
        await message.reply_text(
            _("admin_private_only"),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    _("admin_open_chat"),
                    url=f"https://t.me/{bot_username}?start=my"
                )
            ]])
        )
        return

    await message.reply_text(_chat_list_text(_), reply_markup=get_my_buttons(user_id))
