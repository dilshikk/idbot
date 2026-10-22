import sqlite3
import os
import logging
import threading
from datetime import datetime
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
DEFAULT_LANG = "ru"
NO_USERNAME = "unknown"
LOGGER = logging.getLogger(__name__)

# Одно постоянное подключение вместо нового на каждый запрос:
# открытие файла SQLite было самой медленной частью и тормозило весь бот.
_conn: sqlite3.Connection | None = None
_lock = threading.Lock()

# Язык читается на каждое сообщение, поэтому держим его в памяти.
_lang_cache: dict[int, str] = {}
# Последний известный ник: пишем в базу только когда он реально изменился.
_username_cache: dict[int, str] = {}


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


def init_db():
    try:
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
        LOGGER.info("Database initialized successfully.")
    except Exception as e:
        LOGGER.error(f"Error initializing database: {e}", exc_info=True)


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


def add_user(user) -> bool:
    try:
        lang = (user.language_code or DEFAULT_LANG).split("-")[0]
        username = user.username or NO_USERNAME
        with get_conn() as conn:
            # INSERT OR IGNORE атомарен: нет гонки между проверкой и вставкой
            cursor = conn.execute(
                "INSERT OR IGNORE INTO users (telegram_id, username, lang, reg_date) VALUES (?, ?, ?, ?)",
                (user.id, username, lang, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
        if cursor.rowcount == 0:
            return False
        _lang_cache[user.id] = lang
        _username_cache[user.id] = username
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
            # IS NOT: не перезаписываем строку, если ник в базе уже такой же
            cursor = conn.execute(
                "UPDATE users SET username = ? WHERE telegram_id = ? AND username IS NOT ?",
                (new, telegram_id, new),
            )
        # Запоминаем и для тех, кого ещё нет в базе: add_user сохранит тот же ник
        _username_cache[telegram_id] = new
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
        _lang_cache[telegram_id] = lang
        return lang
    except Exception as e:
        LOGGER.error(f"Error getting language for {telegram_id}: {e}", exc_info=True)
        return DEFAULT_LANG


def set_lang(telegram_id: int, lang: str) -> None:
    try:
        with get_conn() as conn:
            cursor = conn.execute(
                "UPDATE users SET lang = ? WHERE telegram_id = ?", (lang, telegram_id)
            )
        if cursor.rowcount > 0:
            _lang_cache[telegram_id] = lang
        LOGGER.info(f"Language for user {telegram_id} changed to {lang}.")
    except Exception as e:
        LOGGER.error(f"Error setting language for {telegram_id}: {e}", exc_info=True)


def save_payment(payment_id: str, user_id: int, full_name: str, username: str, amount: int, charge_id: str) -> None:
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO payments (id, user_id, full_name, username, amount, charge_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (payment_id, user_id, full_name, username, amount, charge_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
        LOGGER.info(f"💰 Payment saved: id={payment_id}, user={user_id}, amount={amount}")
    except Exception as e:
        LOGGER.error(f"Error saving payment {payment_id}: {e}", exc_info=True)


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
