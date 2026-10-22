from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType
from utils import LOGGER
from database import get_lang
from utils.i18n import get_translator
from miscs.adbtn import get_admin_buttons
from miscs.mybtn import get_my_buttons
from bot import bot, get_bot_username
from config import COMMAND_PREFIX
from modules.callback import _chat_list_text


async def reply_private_only(message, _, start_param: str) -> None:
    """В группе нижнюю клавиатуру показывать нельзя: зовём в личку.
    Ссылка с ?start=... сразу откроет нужный раздел."""
    bot_username = await get_bot_username()
    await message.reply_text(
        _("admin_private_only"),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(_("admin_open_chat"), url=f"https://t.me/{bot_username}?start={start_param}")
        ]]),
    )


async def send_chat_picker(message, user_id: int, kind: str) -> None:
    """kind: "admin" (чаты, где вы админ) или "my" (чаты, которые вы создали)."""
    _ = get_translator(get_lang(user_id))
    if message.chat.type != ChatType.PRIVATE:
        await reply_private_only(message, _, kind)
        return
    keyboard = get_admin_buttons(user_id) if kind == "admin" else get_my_buttons(user_id)
    await message.reply_text(_chat_list_text(_), reply_markup=keyboard)


@bot.on_message(filters.command("admin", prefixes=COMMAND_PREFIX.split("|")))
async def admin_command(client: Client, message):
    if not message.from_user:
        return
    LOGGER.info(f"/admin command from {message.from_user.id} in {message.chat.type}")
    await send_chat_picker(message, message.from_user.id, "admin")
