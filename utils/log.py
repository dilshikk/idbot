import logging
import re

# Токен бота выглядит как 123456:AAH...; вырезаем его из любых строк логов
_TOKEN_RE = re.compile(r"\d{6,}:[A-Za-z0-9_-]{30,}")


class RedactTokenFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        cleaned = _TOKEN_RE.sub("<BOT_TOKEN>", message)
        if cleaned != message:
            record.msg, record.args = cleaned, None
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
for handler in logging.getLogger().handlers:
    handler.addFilter(RedactTokenFilter())

for name in ("pyrogram", "pyrogram.client", "pyrogram.session", "pyrogram.connection"):
    logging.getLogger(name).setLevel(logging.ERROR)

LOGGER = logging.getLogger("TG_iBot")
