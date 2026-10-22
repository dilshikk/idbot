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


def _int_list(raw: str) -> list[int]:
    return [int(x) for x in raw.replace(" ", "").split(",") if x]


_load_env_file(ENV_FILE)

API_ID = int(_required("API_ID"))
API_HASH = _required("API_HASH")
BOT_TOKEN = _required("BOT_TOKEN")

# Один или несколько ID через запятую: ADMIN_ID=123,456
ADMIN_ID = _int_list(_required("ADMIN_ID"))

LOG_GROUP_ID = int(os.environ.get("LOG_GROUP_ID", "0") or 0)
COMMAND_PREFIX = os.environ.get("COMMAND_PREFIX", "#|.|/|!|,")

# Сколько обработчиков работают одновременно. 1000 было слишком много.
WORKERS = int(os.environ.get("WORKERS", "16"))
