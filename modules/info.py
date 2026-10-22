import re

from pyrogram import Client, filters
from utils import LOGGER
from utils.ratelimit import throttle
from bot import bot
from utils.i18n import get_translator
from database import get_lang
from config import COMMAND_PREFIX
from modules.helpers import describe_peer, send_entity_info
from modules.me import send_own_profile

# Разрешаем только юзернейм (5-32 символа, как в Telegram) или числовой ID
_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
_NUMERIC_ID_RE = re.compile(r"^-?\d{1,20}$")
_LINK_PREFIX_RE = re.compile(r"^(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/", re.IGNORECASE)


def parse_target(raw: str) -> int | str | None:
    """Достаёт из аргумента юзернейм или ID. Всё остальное отбрасывается.
    Раньше числа уходили в Telegram как строка и искались как номер телефона."""
    value = _LINK_PREFIX_RE.sub("", raw.strip()).lstrip("@").split("/")[0].split("?")[0]
    if _NUMERIC_ID_RE.match(value):
        return int(value)
    if _USERNAME_RE.match(value):
        return value
    return None


@bot.on_message(filters.private & filters.command(["info", "id"], prefixes=COMMAND_PREFIX.split("|")))
async def info_command(client: Client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    lang = get_lang(user_id)
    _ = get_translator(lang)
    LOGGER.info(f"/info command received from {user_id}")

    args = message.command[1:]
    if not args or args[0].lower() == "me":
        await send_own_profile(client, message, _)
        return

    target = parse_target(args[0])
    if target is None:
        await message.reply_text(_("no_control_over_user"))
        return

    if await throttle(message, lang):
        return

    loading_message = await message.reply_text(_("processing_info"))
    try:
        chat = await client.get_chat(target)
        response, full_name = await describe_peer(client, chat, _)
        await send_entity_info(loading_message, client, chat.id, response, full_name)
    except Exception as e:
        LOGGER.error(f"Error fetching info for {target}: {e}")
        await loading_message.edit_text(_("no_control_over_user"))
