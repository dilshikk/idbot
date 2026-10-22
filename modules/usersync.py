from pyrogram import Client, filters
from bot import bot
from utils import LOGGER
from database import sync_username

# Группа -1 выполняется раньше остальных обработчиков (группа 0) и не мешает им:
# бот просто сверяет ник и дальше обрабатывает сообщение как обычно.
SYNC_GROUP = -1


@bot.on_message(filters.private & filters.incoming, group=SYNC_GROUP)
async def sync_username_on_message(_: Client, message):
    user = message.from_user
    if not user or user.is_bot:
        return
    try:
        sync_username(user.id, user.username)
    except Exception as e:
        LOGGER.error(f"Username sync (message) failed for {user.id}: {e}")


@bot.on_callback_query(group=SYNC_GROUP)
async def sync_username_on_callback(_: Client, query):
    user = query.from_user
    if not user or user.is_bot:
        return
    try:
        sync_username(user.id, user.username)
    except Exception as e:
        LOGGER.error(f"Username sync (callback) failed for {user.id}: {e}")
