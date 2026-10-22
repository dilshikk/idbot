from pyrogram import Client, filters
from pyrogram.enums import ParseMode

from bot import bot
from config import ADMIN_ID, COMMAND_PREFIX
from database import get_stats
from utils import LOGGER
from utils.text import md_escape

LANG_NAMES = {"ru": "🇷🇺 ru", "en": "🇬🇧 en", "uz": "🇺🇿 uz"}
DIVIDER = "━━━━━━━━━━━━━━━"


def _pct(part: int, total: int) -> str:
    return f"{part * 100 / total:.1f}%" if total else "0%"


def _format_stats(s: dict) -> str:
    users = s["users"]
    pay = s["payments"]
    total = users["total"]

    langs = "\n".join(
        f"  {LANG_NAMES.get(lang, md_escape(lang))}: {count} ({_pct(count, total)})"
        for lang, count in users["by_lang"]
    ) or "  нет данных"

    top = "\n".join(
        f"  {i}. {md_escape(name)} (`{uid}`): {amount} ⭐️"
        for i, (uid, name, amount) in enumerate(pay["top"], start=1)
    ) or "  пока нет"

    return (
        f"**📊 Статистика бота**\n**{DIVIDER}**\n"
        f"**👥 Пользователи**\n"
        f"  Всего: **{total}**\n"
        f"  Новых за 24 часа: {users['day']}\n"
        f"  Новых за 7 дней: {users['week']}\n"
        f"  Новых за 30 дней: {users['month']}\n\n"
        f"**🌐 Языки**\n{langs}\n\n"
        f"**⭐️ Донаты** (без возвратов)\n"
        f"  Всего: {pay['count']} шт. на **{pay['sum']} ⭐️**\n"
        f"  За 7 дней: {pay['week_count']} шт. на {pay['week_sum']} ⭐️\n"
        f"  За 30 дней: {pay['month_count']} шт. на {pay['month_sum']} ⭐️\n"
        f"  Возвращено: {pay['refunded_count']} шт. на {pay['refunded_sum']} ⭐️\n\n"
        f"**🏆 Топ донатеров**\n{top}\n"
        f"**{DIVIDER}**"
    )


# filters.user пропускает только админов: остальным бот просто не отвечает.
# Только в личке, чтобы цифры не увидели в группе.
@bot.on_message(
    filters.private
    & filters.user(ADMIN_ID)
    & filters.command("stats", prefixes=COMMAND_PREFIX.split("|"))
)
async def stats_command(client: Client, message):
    LOGGER.info(f"/stats requested by {message.from_user.id}")
    stats = get_stats()
    if stats is None:
        await message.reply_text("❌ Не удалось получить статистику, подробности в логах.")
        return
    await message.reply_text(_format_stats(stats), parse_mode=ParseMode.MARKDOWN)
