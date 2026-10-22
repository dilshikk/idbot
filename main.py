import logging
import threading
import time

import requests
from pyrogram import idle

from bot import bot
from database.db import init_db
from utils import LOGGER
from utils.log import RedactTokenFilter
from config import BOT_TOKEN, LOG_GROUP_ID

# Порядок важен: внутри одной группы срабатывает первый подходящий обработчик.
from core.start import start  # noqa: F401
from modules.usersync import sync_username_on_message, sync_username_on_callback  # noqa: F401
from modules.menu import settings_menu, setup_bot_commands  # noqa: F401
from modules.help import help_command  # noqa: F401
from modules.my import my_command  # noqa: F401
from modules.admin import admin_command  # noqa: F401
from modules.stats import stats_command  # noqa: F401
from modules.language import choose_language, set_user_language  # noqa: F401
from modules.me import me_command  # noqa: F401
from modules.info import info_command  # noqa: F401
from modules.donate import donate_command  # noqa: F401
from modules.fwd import handle_forwarded_message  # noqa: F401
from modules.username import username_command  # noqa: F401
from modules.callback import admin_button_handler, owner_button_handler  # noqa: F401
from shared.chatinfo import handle_message  # noqa: F401

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramHandler(logging.Handler):
    """Отправляет ошибки в группу логов.
    Не чаще одного сообщения в MIN_INTERVAL секунд: раньше поток ошибок
    создавал сотни потоков и упирался в лимиты Telegram."""

    MIN_INTERVAL = 3.0
    MAX_LEN = 3900

    def __init__(self):
        super().__init__()
        self.api_url = f"{TELEGRAM_API_BASE}/bot{BOT_TOKEN}/sendMessage"
        self._last_sent = 0.0
        self._suppressed = 0
        self._lock = threading.Lock()

    def emit(self, record):
        try:
            with self._lock:
                now = time.monotonic()
                if now - self._last_sent < self.MIN_INTERVAL:
                    self._suppressed += 1
                    return
                self._last_sent = now
                suppressed, self._suppressed = self._suppressed, 0

            text = self.format(record)[-self.MAX_LEN:]
            header = "🚨 TG_iBot Error Log"
            if suppressed:
                header += f" (+{suppressed} skipped)"
            threading.Thread(target=self._send_log, args=(f"{header}\n\n{text}",), daemon=True).start()
        except Exception:
            self.handleError(record)

    def _send_log(self, message: str):
        try:
            # Без parse_mode: текст ошибки может сломать разметку, и лог потеряется
            requests.post(
                self.api_url,
                data={"chat_id": LOG_GROUP_ID, "text": message, "disable_web_page_preview": True},
                timeout=5,
            )
        except Exception as e:
            # не выводим e целиком: в тексте ошибки requests может оказаться URL с токеном
            print(f"[Logger Error] Telegram send failed: {type(e).__name__}")


def setup_logging() -> None:
    # basicConfig уже вызван в utils/log.py, поэтому прошлый вызов здесь
    # ничего не делал, и ошибки в группу логов вообще не приходили.
    handler = TelegramHandler()
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    handler.addFilter(RedactTokenFilter())
    logging.getLogger().addHandler(handler)


async def main():
    await bot.start()
    # Список команд в кнопке «Меню» Telegram обновляется при каждом запуске
    await setup_bot_commands(bot)
    LOGGER.info("🚀 TG_iBot Started Successfully 💥")
    await idle()
    await bot.stop()


if __name__ == "__main__":
    setup_logging()

    LOGGER.info("🗃 Initializing database...")
    try:
        init_db()
        LOGGER.info("✅ Database initialized successfully.")
    except Exception:
        # Раньше бот запускался без базы и падал на каждом сообщении
        LOGGER.exception("❌ Database initialization failed, bot stopped")
        raise SystemExit(1)

    try:
        bot.run(main())
    except Exception:
        LOGGER.exception("💥 Critical bot failure")
        raise SystemExit(1)
