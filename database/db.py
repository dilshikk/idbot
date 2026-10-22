import sqlite3
import os
import logging
from datetime import datetime
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
LOGGER = logging.getLogger(__name__)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
        with get_conn() as conn:
            existing = conn.execute(
                "SELECT 1 FROM users WHERE telegram_id = ?", (user.id,)
            ).fetchone()
            if existing:
                return False
            lang = (user.language_code or "ru").split("-")[0]
            username = user.username or "unknown"
            conn.execute(
                "INSERT INTO users (telegram_id, username, lang, reg_date) VALUES (?, ?, ?, ?)",
                (user.id, username, lang, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            LOGGER.info(f"🆕 New user: id={user.id}, @{username}, lang={lang}")
            return True
    except Exception as e:
        LOGGER.error(f"Error adding user {getattr(user, 'id', '?')}: {e}", exc_info=True)
        return False


def get_lang(telegram_id: int) -> str:
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT lang FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
        return row["lang"] if row else "ru"
    except Exception as e:
        LOGGER.error(f"Error getting language for {telegram_id}: {e}", exc_info=True)
        return "ru"


def set_lang(telegram_id: int, lang: str) -> None:
    try:
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET lang = ? WHERE telegram_id = ?", (lang, telegram_id)
            )
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
