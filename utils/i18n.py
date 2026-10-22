import os
from functools import lru_cache

import yaml

LOCALES_DIR = os.path.join(os.path.dirname(__file__), "..", "locales")
DEFAULT_LANG = "en"

# Единый список поддерживаемых языков. Чтобы добавить язык,
# допишите его сюда и положите файл locales/<код>.yaml
LANGUAGES = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "uz": "🇺🇿 Oʻzbekcha",
}


@lru_cache(maxsize=None)
def load_translations(lang: str) -> dict:
    # Код языка подставляется в путь к файлу, поэтому пускаем только известные языки
    if lang not in LANGUAGES:
        lang = DEFAULT_LANG
    path = os.path.join(LOCALES_DIR, f"{lang}.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_translator(lang: str):
    translations = load_translations(lang)

    def _(key: str) -> str:
        return translations.get(key, key)

    return _


@lru_cache(maxsize=None)
def button_variants(key: str) -> frozenset[str]:
    """Текст кнопки на всех языках. Считается один раз, а не на каждое сообщение."""
    return frozenset(
        load_translations(lang)[key]
        for lang in LANGUAGES
        if key in load_translations(lang)
    )
