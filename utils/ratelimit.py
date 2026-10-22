"""Ограничение частоты запросов от одного пользователя.

Поиск по юзернейму и пересылки вызывают тяжёлые запросы к Telegram.
Без ограничения один человек мог завалить бота запросами, Telegram
отвечал FloodWait, и бот замирал для всех пользователей.
"""
import time

LOOKUP_INTERVAL = 2.0   # не чаще одного поиска в 2 секунды
NOTICE_INTERVAL = 10.0  # предупреждение о лимите не чаще раза в 10 секунд
_MAX_KEYS = 50_000

_last_hit: dict[tuple[str, int], float] = {}

_RATE_LIMIT_TEXT = {
    "ru": "⏳ Слишком часто. Подождите пару секунд и попробуйте снова.",
    "en": "⏳ Too many requests. Please wait a couple of seconds.",
    "uz": "⏳ Juda tez-tez. Bir necha soniya kuting va qayta urinib ko'ring.",
}


def _prune(now: float) -> None:
    stale = [key for key, ts in _last_hit.items() if now - ts >= NOTICE_INTERVAL]
    for key in stale:
        del _last_hit[key]
    if len(_last_hit) >= _MAX_KEYS:
        _last_hit.clear()


def is_limited(user_id: int, action: str, interval: float) -> bool:
    """True, если пользователь уже делал это действие меньше interval секунд назад."""
    now = time.monotonic()
    key = (action, user_id)
    last = _last_hit.get(key)
    if last is not None and now - last < interval:
        return True
    if len(_last_hit) >= _MAX_KEYS:
        _prune(now)
    _last_hit[key] = now
    return False


async def throttle(message, lang: str, action: str = "lookup") -> bool:
    """True, если запрос нужно пропустить. Предупреждает пользователя, но не спамит."""
    user_id = message.from_user.id
    if not is_limited(user_id, action, LOOKUP_INTERVAL):
        return False
    if not is_limited(user_id, f"{action}_notice", NOTICE_INTERVAL):
        try:
            await message.reply_text(_RATE_LIMIT_TEXT.get(lang, _RATE_LIMIT_TEXT["en"]))
        except Exception:
            pass
    return True
