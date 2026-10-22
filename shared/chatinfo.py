from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import LOGGER
from bot import bot
from database import get_lang
from utils.i18n import get_translator


async def _reply_with_optional_photo(message, photo_file_id, text: str, markup: InlineKeyboardMarkup):
    if photo_file_id:
        await message.reply_photo(photo=photo_file_id, caption=text, reply_markup=markup)
    else:
        await message.reply_text(text, reply_markup=markup)


@bot.on_message(filters.private)
async def handle_message(bot: Client, message):
    if not message.from_user:
        await message.delete()
        return

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))

    LOGGER.info(f"Handling shared chat/user message from {user_id}")

    shared = getattr(message, "chats_shared", None)
    if not shared:
        return

    if getattr(shared, "chats", None):
        for chat in shared.chats:
            chat_id = chat.chat_id
            chat_name = chat.name or _("unnamed_chat")
            chat_type = str(chat.chat_type).replace("ChatType.", "").capitalize()
            username = f"@{chat.username}" if chat.username else _("no_username")

            text = (
                f"ℹ️ **{_('shared_chat_info')}**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🏷 {_('type_label')}: `{chat_type}`\n"
                f"🆔 {_('id_label')}: `{chat_id}`\n"
                f"💬 {_('name_label')}: `{chat_name}`\n"
                f"🔗 {_('username_label')}: `{username}`"
            )
            markup = InlineKeyboardMarkup([[
                InlineKeyboardButton(text=chat_name, copy_text=str(chat_id))
            ]])
            photo = getattr(getattr(chat, "photo", None), "file_id", None)
            await _reply_with_optional_photo(message, photo, text, markup)

    elif getattr(shared, "users", None):
        for user in shared.users:
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            username = f"@{user.username}" if user.username else _("no_username")
            user_type = _("bot_label") if (user.username and user.username.lower().endswith("bot")) else _("user_label")

            text = (
                f"ℹ️ **{_('shared_info')} {user_type} {_('info_label')}**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🆔 {_('id_label')}: `{user.user_id}`\n"
                f"👤 {_('name_label')}: `{full_name}`\n"
                f"🔗 {_('username_label')}: `{username}`\n"
                f"🏷 {_('type_label')}: `{user_type}`"
            )
            markup = InlineKeyboardMarkup([[
                InlineKeyboardButton(text=full_name, copy_text=str(user.user_id))
            ]])
            photo = getattr(getattr(user, "photo", None), "file_id", None)
            await _reply_with_optional_photo(message, photo, text, markup)
