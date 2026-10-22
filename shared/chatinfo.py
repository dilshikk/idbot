from pyrogram import Client, filters
from utils import LOGGER
from utils.text import md_escape
from bot import bot
from database import get_lang
from utils.i18n import get_translator
from modules.helpers import copy_button, display_name


async def _reply_with_optional_photo(message, photo_file_id, text: str, markup):
    if photo_file_id:
        try:
            await message.reply_photo(photo=photo_file_id, caption=text, reply_markup=markup)
            return
        except Exception as e:
            LOGGER.error(f"Shared photo failed, sending text instead: {e}")
    await message.reply_text(text, reply_markup=markup)


def _has_shared(_, __, message) -> bool:
    return bool(getattr(message, "chats_shared", None))


# Раньше обработчик ловил вообще все личные сообщения и писал о каждом в лог.
# Теперь срабатывает только когда пользователь поделился чатом через кнопку.
@bot.on_message(filters.private & filters.create(_has_shared))
async def handle_message(client: Client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))
    LOGGER.info(f"Handling shared chat/user message from {user_id}")
    shared = message.chats_shared

    try:
        for chat in getattr(shared, "chats", None) or []:
            chat_name = (chat.name or "").strip() or _("unnamed_chat")
            chat_type = str(chat.chat_type).replace("ChatType.", "").capitalize()
            username = f"@{chat.username}" if chat.username else _("no_username")

            text = (
                f"ℹ️ **{_('shared_chat_info')}**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🏷 {_('type_label')}: `{md_escape(chat_type)}`\n"
                f"🆔 {_('id_label')}: `{chat.chat_id}`\n"
                f"💬 {_('name_label')}: `{md_escape(chat_name)}`\n"
                f"🔗 {_('username_label')}: `{md_escape(username)}`"
            )
            photo = getattr(getattr(chat, "photo", None), "file_id", None)
            await _reply_with_optional_photo(message, photo, text, copy_button(chat_name, str(chat.chat_id)))

        for user in getattr(shared, "users", None) or []:
            full_name = display_name(user.first_name, user.last_name, _("unknown"))
            username = f"@{user.username}" if user.username else _("no_username")
            is_bot = bool(user.username and user.username.lower().endswith("bot"))
            user_type = _("bot_label") if is_bot else _("user_label")

            text = (
                f"ℹ️ **{_('shared_info')} {user_type} {_('info_label')}**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🆔 {_('id_label')}: `{user.user_id}`\n"
                f"👤 {_('name_label')}: `{md_escape(full_name)}`\n"
                f"🔗 {_('username_label')}: `{md_escape(username)}`\n"
                f"🏷 {_('type_label')}: `{user_type}`"
            )
            photo = getattr(getattr(user, "photo", None), "file_id", None)
            await _reply_with_optional_photo(message, photo, text, copy_button(full_name, str(user.user_id)))

    except Exception as e:
        LOGGER.error(f"Error handling shared chat for {user_id}: {e}", exc_info=True)
