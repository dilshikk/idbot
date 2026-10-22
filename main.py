import logging
import requests
import threading
from bot import bot
from database.db import init_db
from utils import LOGGER
from core.start import start
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
from shared.chatinfo import handle_message
from config import BOT_TOKEN, LOG_GROUP_ID


# =====================
# 📦 Telegram Log Handler
# =====================
class TelegramHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.api_url = f"http://176.101.56.195:8081/bot{BOT_TOKEN}/sendMessage"

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
            print(f"[Logger Error] Telegram send failed: {e}")


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

LOGGER.info("🚀 TG_iBot Started Successfully 💥")

try:
    bot.run()
except Exception as e:
    LOGGER.exception("💥 Critical bot failure: %s", e)
