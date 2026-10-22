"""
Настройки бота читаются из переменных окружения или из файла .env рядом с этим файлом.
Секреты в коде больше не хранятся. Пример: .env.example
"""
import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"


def _load_env_file(path: Path) -> None:
    """Простой загрузчик .env без внешних зависимостей.
    Уже заданные переменные окружения не перезаписываются."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Не задана переменная окружения {name}. Смотрите .env.example")
    return value


def _int(name: str, raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        # Значение не печатаем целиком: туда по ошибке мог попасть секрет
        raise RuntimeError(f"Переменная {name} должна быть числом") from None


def _int_list(name: str, raw: str) -> list[int]:
    return [_int(name, x) for x in raw.replace(" ", "").split(",") if x]


_load_env_file(ENV_FILE)

API_ID = _int("API_ID", _required("API_ID"))
API_HASH = _required("API_HASH")
BOT_TOKEN = _required("BOT_TOKEN")

# Один или несколько ID через запятую: ADMIN_ID=123,456
ADMIN_ID = _int_list("ADMIN_ID", _required("ADMIN_ID"))
if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID должен содержать хотя бы один ID")

# Обязательна: сюда бот пишет о новых пользователях и ошибках
LOG_GROUP_ID = _int("LOG_GROUP_ID", _required("LOG_GROUP_ID"))
COMMAND_PREFIX = os.environ.get("COMMAND_PREFIX", "#|.|/|!|,")

# Сколько обработчиков работают одновременно (от 1 до 64)
WORKERS = min(max(_int("WORKERS", os.environ.get("WORKERS", "16")), 1), 64)
