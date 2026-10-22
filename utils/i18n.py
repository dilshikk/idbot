import yaml
import os
from functools import lru_cache

LOCALES_DIR = os.path.join(os.path.dirname(__file__), "..", "locales")
DEFAULT_LANG = "en"


@lru_cache(maxsize=10)
def load_translations(lang: str) -> dict:
    path = os.path.join(LOCALES_DIR, f"{lang}.yaml")
    if not os.path.exists(path):
        path = os.path.join(LOCALES_DIR, f"{DEFAULT_LANG}.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_translator(lang: str):
    translations = load_translations(lang)

    def _(key: str) -> str:
        return translations.get(key, key) 

    return _
