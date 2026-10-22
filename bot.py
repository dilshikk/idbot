from pyrogram import Client
from pyrogram.enums import ParseMode
from utils import LOGGER
from config import API_ID, API_HASH, BOT_TOKEN

LOGGER.info("Creating Bot Client From BOT_TOKEN")
bot = Client(
    "TG_iBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=1000,
    parse_mode=ParseMode.MARKDOWN,
)
LOGGER.info("Bot Client Created Successfully!")

_bot_username: str | None = None

async def get_bot_username() -> str:
    global _bot_username
    if _bot_username is None:
        me = await bot.get_me()
        _bot_username = me.username or ""
    return _bot_username
