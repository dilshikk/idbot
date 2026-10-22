from googletrans import Translator
from pathlib import Path
import re

translator = Translator()
src = Path("messages.po").read_text(encoding="utf-8")


def translate_block(block: str) -> str:
    match = re.search(r'msgid "(.*)"\nmsgstr ""', block, re.S)
    if not match:
        return block

    text = match.group(1).replace('\n"', '').replace('"', '')
    if not text.strip():
        return block

    try:
        translated = translator.translate(text, src="en", dest="ru").text  # ← исправлено
    except Exception:
        translated = text

    return re.sub(r'msgstr ""', f'msgstr "{translated}"', block, count=1)


parts = re.split(r'\n\n+', src)
result = "\n\n".join(translate_block(p) for p in parts)
Path("messages_ru.po").write_text(result, encoding="utf-8")
print("✅ Переведённый файл сохранён как messages_ru.po")  # ← исправлено
