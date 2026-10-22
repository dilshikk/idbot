import sqlite3
import os
import logging
import threading
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
DEFAULT_LANG = "ru"
NO_USERNAME = "unknown"
LOGGER = logging.getLogger(__name__)

# Одно постоянное подключение вместо нового на каждый запрос
_conn: sqlite3.Connection | None = None
_lock = threading.Lock()

# Язык читается на каждое сообщение, поэтому держим его в памяти.
_lang_cache: dict[int, str] = {}
# Последний известный ник: пишем в базу только когда он реально изменился.
_username_cache: dict[int, str] = {}
# Защита от разрастания памяти при большом числе пользователей
_CACHE_LIMIT = 200_000

_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TOP_DONORS_LIMIT = 5


def _now() -> str:
    return datetime.now(timezone.utc).strftime(_TIME_FORMAT)


def _since(days: int) -> str:
    """Момент N дней назад в том же формате, что reg_date и created_at.
    Формат одинаковый, поэтому даты можно сравнивать как строки."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime(_TIME_FORMAT)


def _remember(cache: dict, key: int, value: str) -> None:
    if len(cache) >= _CACHE_LIMIT:
        cache.clear()
    cache[key] = value


def _get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5)
        _conn.row_factory = sqlite3.Row
        # WAL: чтение не ждёт записи, запись быстрее
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("PRAGMA busy_timeout=5000")
    return _conn


@contextmanager
def get_conn():
    with _lock:
        conn = _get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        LOGGER.info(f"Database migrated: {table}.{column} added")


def init_db() -> None:
    """Создаёт таблицы. Ошибку пробрасывает дальше: без базы бот работать не должен."""
    os.makedirs(BASE_DIR, exist_ok=True)
    LOGGER.info(f"Database path: {DB_PATH}")
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                lang TEXT DEFAULT 'ru',
                reg_date TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                full_name TEXT,
                username TEXT,
                amount INTEGER,
                charge_id TEXT,
                created_at TEXT
            )
        """)
        # Отметка о возврате: раньше один платёж можно было пытаться вернуть много раз
        _add_column_if_missing(conn, "payments", "refunded_at", "refunded_at TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_charge ON payments(charge_id)")
        # Для быстрого подсчёта новых пользователей и донатов за период
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reg_date ON users(reg_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at)")


def user_exists(telegram_id: int) -> bool:
    if telegram_id in _lang_cache:
        return True
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
        return row is not None
    except Exception as e:
        LOGGER.error(f"Error checking user existence for {telegram_id}: {e}", exc_info=True)
        return False


def add_user(user, lang: str | None = None) -> bool:
    try:
        lang = lang or (user.language_code or DEFAULT_LANG).split("-")[0]
        username = user.username or NO_USERNAME
        with get_conn() as conn:
            # INSERT OR IGNORE атомарен: нет гонки между проверкой и вставкой
            cursor = conn.execute(
                "INSERT OR IGNORE INTO users (telegram_id, username, lang, reg_date) VALUES (?, ?, ?, ?)",
                (user.id, username, lang, _now()),
            )
        if cursor.rowcount == 0:
            return False
        _remember(_lang_cache, user.id, lang)
        _remember(_username_cache, user.id, username)
        LOGGER.info(f"🆕 New user: id={user.id}, @{username}, lang={lang}")
        return True
    except Exception as e:
        LOGGER.error(f"Error adding user {getattr(user, 'id', '?')}: {e}", exc_info=True)
        return False


def sync_username(telegram_id: int, username: str | None) -> bool:
    """Обновляет ник в базе, если пользователь его сменил.
    Возвращает True, если запись в базе изменилась."""
    new = username or NO_USERNAME
    if _username_cache.get(telegram_id) == new:
        return False  # ник не менялся: базу не трогаем
    try:
        with get_conn() as conn:
            cursor = conn.execute(
                "UPDATE users SET username = ? WHERE telegram_id = ? AND username IS NOT ?",
                (new, telegram_id, new),
            )
        _remember(_username_cache, telegram_id, new)
        if cursor.rowcount > 0:
            LOGGER.info(f"✏️ Username updated: id={telegram_id} -> @{new}")
            return True
        return False
    except Exception as e:
        LOGGER.error(f"Error syncing username for {telegram_id}: {e}", exc_info=True)
        return False


def get_lang(telegram_id: int) -> str:
    cached = _lang_cache.get(telegram_id)
    if cached:
        return cached
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT lang FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
        if not row:
            return DEFAULT_LANG  # не кэшируем: пользователя ещё нет в базе
        lang = row["lang"] or DEFAULT_LANG
        _remember(_lang_cache, telegram_id, lang)
        return lang
    except Exception as e:
        LOGGER.error(f"Error getting language for {telegram_id}: {e}", exc_info=True)
        return DEFAULT_LANG


def set_lang(telegram_id: int, lang: str) -> bool:
    """Возвращает True, если язык сохранён (пользователь есть в базе)."""
    try:
        with get_conn() as conn:
            cursor = conn.execute(
                "UPDATE users SET lang = ? WHERE telegram_id = ?", (lang, telegram_id)
            )
        if cursor.rowcount == 0:
            return False
        _remember(_lang_cache, telegram_id, lang)
        LOGGER.info(f"Language for user {telegram_id} changed to {lang}.")
        return True
    except Exception as e:
        LOGGER.error(f"Error setting language for {telegram_id}: {e}", exc_info=True)
        return False


def save_payment(payment_id: str, user_id: int, full_name: str, username: str, amount: int, charge_id: str) -> bool:
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO payments (id, user_id, full_name, username, amount, charge_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (payment_id, user_id, full_name, username, amount, charge_id, _now()),
            )
        LOGGER.info(f"💰 Payment saved: id={payment_id}, user={user_id}, amount={amount}")
        return True
    except Exception as e:
        LOGGER.error(f"Error saving payment {payment_id}: {e}", exc_info=True)
        return False


def get_payment(payment_id: str) -> dict | None:
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        LOGGER.error(f"Error getting payment {payment_id}: {e}", exc_info=True)
        return None


def claim_refund(payment_id: str) -> bool:
    """Атомарно помечает платёж как возвращённый.
    False, если платёж уже возвращён (защита от двойного нажатия)."""
    with get_conn() as conn:
        cursor = conn.execute(
            "UPDATE payments SET refunded_at = ? WHERE id = ? AND refunded_at IS NULL",
            (_now(), payment_id),
        )
    return cursor.rowcount > 0


def release_refund(payment_id: str) -> None:
    """Снимает отметку, если Telegram не принял возврат."""
    with get_conn() as conn:
        conn.execute("UPDATE payments SET refunded_at = NULL WHERE id = ?", (payment_id,))


def get_stats() -> dict | None:
    """Сводка для /stats. Донаты считаются без возвращённых.
    None, если база недоступна."""
    day, week, month = _since(1), _since(7), _since(30)
    try:
        with get_conn() as conn:
            users = conn.execute(
                """SELECT COUNT(*) AS total,
                          COALESCE(SUM(reg_date >= ?), 0) AS day,
                          COALESCE(SUM(reg_date >= ?), 0) AS week,
                          COALESCE(SUM(reg_date >= ?), 0) AS month
                   FROM users""",
                (day, week, month),
            ).fetchone()
            by_lang = conn.execute(
                """SELECT COALESCE(lang, ?) AS lang, COUNT(*) AS cnt
                   FROM users GROUP BY 1 ORDER BY cnt DESC""",
                (DEFAULT_LANG,),
            ).fetchall()
            pay = conn.execute(
                """SELECT
                     COALESCE(SUM(refunded_at IS NULL), 0) AS cnt,
                     COALESCE(SUM(CASE WHEN refunded_at IS NULL THEN amount END), 0) AS total,
                     COALESCE(SUM(refunded_at IS NULL AND created_at >= ?), 0) AS week_cnt,
                     COALESCE(SUM(CASE WHEN refunded_at IS NULL AND created_at >= ? THEN amount END), 0) AS week_sum,
                     COALESCE(SUM(refunded_at IS NULL AND created_at >= ?), 0) AS month_cnt,
                     COALESCE(SUM(CASE WHEN refunded_at IS NULL AND created_at >= ? THEN amount END), 0) AS month_sum,
                     COALESCE(SUM(refunded_at IS NOT NULL), 0) AS ref_cnt,
                     COALESCE(SUM(CASE WHEN refunded_at IS NOT NULL THEN amount END), 0) AS ref_sum
                   FROM payments""",
                (week, week, month, month),
            ).fetchone()
            top = conn.execute(
                """SELECT user_id, MAX(full_name) AS name, SUM(amount) AS total
                   FROM payments WHERE refunded_at IS NULL
                   GROUP BY user_id ORDER BY total DESC LIMIT ?""",
                (TOP_DONORS_LIMIT,),
            ).fetchall()
    except Exception as e:
        LOGGER.error(f"Error collecting stats: {e}", exc_info=True)
        return None

    return {
        "users": {
            "total": users["total"],
            "day": users["day"],
            "week": users["week"],
            "month": users["month"],
            "by_lang": [(row["lang"], row["cnt"]) for row in by_lang],
        },
        "payments": {
            "count": pay["cnt"],
            "sum": pay["total"],
            "week_count": pay["week_cnt"],
            "week_sum": pay["week_sum"],
            "month_count": pay["month_cnt"],
            "month_sum": pay["month_sum"],
            "refunded_count": pay["ref_cnt"],
            "refunded_sum": pay["ref_sum"],
            "top": [(row["user_id"], row["name"] or str(row["user_id"]), row["total"]) for row in top],
        },
    }
