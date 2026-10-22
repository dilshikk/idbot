"""Безопасная вставка пользовательских данных в сообщения с Markdown.

Pyrogram в режиме Markdown сначала превращает разметку в HTML, а потом
разбирает HTML. Поэтому имя вроде `<a href="...">` или `[текст](ссылка)`
раньше превращалось в настоящую ссылку прямо в сообщении бота
(в том числе в группе логов и в уведомлениях админам о донатах).
"""
import html
import re

_ZWSP = "\u200b"  # невидимый пробел
# Двойные разделители Pyrogram: **, __, --, ~~, ||
_DOUBLE_DELIM_RE = re.compile(r"([*_\-~|])(?=\1)")


def md_escape(value: object) -> str:
    """Превращает любое значение в текст, который не может сломать разметку."""
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = html.escape(text, quote=False)
    text = _DOUBLE_DELIM_RE.sub(r"\1" + _ZWSP, text)
    text = text.replace("`", "\u02cb")  # одиночная ` открывает блок кода
    text = text.replace("](", "]" + _ZWSP + "(")  # ломаем [текст](ссылка)
    return text
