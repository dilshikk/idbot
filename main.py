import logging
import requests
import threading
from pyrogram import idle
from bot import bot
from database.db import init_db
from utils import LOGGER
from core.start import start
from modules.usersync import sync_username_on_message, sync_username_on_callback
from modules.menu import settings_menu, setup_bot_commands
from modules.help import help_command
from modules.my import my_command
from modules.admin import admin_command
from modules.language import choose_language, set_user_language
from modules.me import me_command
from modules.info import info_command
from modules.donate import donate_command
from modules.fwd import handle_forwarded_message
from modules.username import username_command
from modules.callback import admin_button_handler, owner_button_handler
# chatinfo ловит все личные сообщения, поэтому подключается последним
from shared.chatinfo import handle_message
from config import BOT_TOKEN, LOG_GROUP_ID

# Официальный Telegram Bot API по HTTPS.
# Раньше логи шли по HTTP на сторонний IP, и токен бота передавался открытым текстом.
TELEGRAM_API_BASE = "https://api.telegram.org"


# =====================
# 📦 Telegram Log Handler
# =====================
class TelegramHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.api_url = f"{TELEGRAM_API_BASE}/bot{BOT_TOKEN}/sendMessage"

    def emit(self, record):
        try:
            log_entry = self.format(record)
            if len(log_entry) > 4000:
                log_entry = log_entry[-4000:]

            # безопасный текст для Markdown
            safe_text = (
                log_entry.replace("_", "\\_")
                         .replace("*", "\\*")
                         .replace("[", "\\[")
                         .replace("`", "'")
            )

            message = f"🚨 *TG_iBot Error Log*\n\n```{safe_text}```"

            # отправляем лог в отдельном потоке (чтобы не блокировать)
            threading.Thread(
                target=self._send_log,
                args=(message,),
                daemon=True
            ).start()

        except Exception as e:
            print(f"[Logger Error] Can't send log: {e}")

    def _send_log(self, message: str):
        try:
            requests.post(
                self.api_url,
                data={
                    "chat_id": LOG_GROUP_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                },
                timeout=5
            )
        except Exception as e:
            # не выводим e целиком: в тексте ошибки requests может оказаться URL с токеном
            print(f"[Logger Error] Telegram send failed: {type(e).__name__}")


# =====================
# 🧠 Настройка логирования
# =====================
telegram_handler = TelegramHandler()
telegram_handler.setLevel(logging.ERROR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[telegram_handler, logging.StreamHandler()]
)

LOGGER.info("🗃 Initializing database...")
try:
    init_db()
    LOGGER.info("✅ Database initialized successfully.")
except Exception as e:
    LOGGER.exception("❌ Database initialization failed: %s", e)


async def main():
    await bot.start()
    # Список команд в кнопке «Меню» Telegram обновляется при каждом запуске
    await setup_bot_commands(bot)
    LOGGER.info("🚀 TG_iBot Started Successfully 💥")
    await idle()
    await bot.stop()


try:
    bot.run(main())
except Exception as e:
    LOGGER.exception("💥 Critical bot failure: %s", e)
