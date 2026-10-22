from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from pyrogram.enums import ChatType, UserStatus
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaAnimation,
)

from utils import LOGGER
from utils.text import md_escape

# У Telegram ровно 5 продакшн дата-центров.
# DC1 и DC3 находятся в Майами, DC2 и DC4 в Амстердаме, DC5 в Сингапуре.
DC_LOCATIONS = {
    1: "MIA, Miami, USA, US",
    2: "AMS, Amsterdam, Netherlands, NL",
    3: "MIA, Miami, USA, US",
    4: "AMS, Amsterdam, Netherlands, NL",
    5: "SIN, Singapore, SG",
}

# Опорные точки «ID -> примерная дата регистрации», по возрастанию ID.
_ID_DATE_POINTS = [
    (100_000_000, datetime(2013, 8, 1)),
    (1_273_841_502, datetime(2020, 8, 13)),
    (1_500_000_000, datetime(2021, 5, 1)),
    (2_000_000_000, datetime(2022, 12, 1)),
]
_MIN_DATE = datetime(2013, 8, 1)  # запуск Telegram
_COPY_TEXT_LIMIT = 256  # лимит Telegram для copy_text
_BUTTON_TEXT_LIMIT = 64


def calculate_account_age(creation_date, _=lambda x: x):
    delta = relativedelta(datetime.now(), creation_date)
    return (
        f"{delta.years} {_('years')}, "
        f"{delta.months} {_('months')}, "
        f"{delta.days} {_('days')}"
    )


def estimate_account_creation_date(user_id: int) -> datetime:
    """Линейная интерполяция между опорными точками.
    Раньше бралась ближайшая точка + фиксированный шаг, и у новых аккаунтов
    (ID больше 5-6 млрд) дата уходила в будущее, а возраст был отрицательным."""
    points = _ID_DATE_POINTS
    if user_id <= points[0][0]:
        return _MIN_DATE

    for (id_a, date_a), (id_b, date_b) in zip(points, points[1:]):
        if user_id <= id_b:
            ratio = (user_id - id_a) / (id_b - id_a)
            return date_a + (date_b - date_a) * ratio

    # Выше последней точки продолжаем по наклону последнего отрезка
    (id_a, date_a), (id_b, date_b) = points[-2], points[-1]
    seconds_per_id = (date_b - date_a).total_seconds() / (id_b - id_a)
    estimate = date_b + timedelta(seconds=(user_id - id_b) * seconds_per_id)
    return min(estimate, datetime.now())


def get_status_display(status, _=lambda x: x):
    if not status:
        return _("unknown")
    status_map = {
        UserStatus.ONLINE:      "status_online",
        UserStatus.OFFLINE:     "status_offline",
        UserStatus.RECENTLY:    "status_recently",
        UserStatus.LAST_WEEK:   "status_last_week",
        UserStatus.LAST_MONTH:  "status_last_month",
        UserStatus.LONG_AGO:    "status_long_ago",
    }
    return _(status_map.get(status, "unknown"))


def get_dc_location(dc_id: int | None, _=lambda x: x) -> str:
    # dc_id известен только если у профиля есть публичное фото, иначе он None/0
    location = DC_LOCATIONS.get(dc_id or 0)
    return f"DC{dc_id} · {location}" if location else _("unknown")


async def get_profile_photo_file_id(client, entity_id):
    try:
        async for photo in client.get_chat_photos(entity_id, limit=1):
            is_animated = bool(getattr(photo, "video_sizes", None))
            return photo.file_id, is_animated
    except Exception as e:
        LOGGER.error(f"Error getting chat photos for {entity_id}: {e}")
    return None, False


def copy_button(label: str, value: str) -> InlineKeyboardMarkup:
    """Кнопка «скопировать». Пустой или слишком длинный текст Telegram отвергает,
    из-за чего раньше падала отправка всего ответа."""
    label = (label or "").strip()[:_BUTTON_TEXT_LIMIT] or "ID"
    value = (value or label)[:_COPY_TEXT_LIMIT]
    return InlineKeyboardMarkup([[InlineKeyboardButton(text=label, copy_text=value)]])


async def send_entity_info(loading_message, client, entity_id: int | None, response: str, full_name: str):
    """Заменяет сообщение «Обрабатываю…» карточкой с фото профиля (если есть).
    Общая функция для /me, /info, пересылок и поиска по юзернейму."""
    buttons = copy_button(full_name, str(entity_id) if entity_id else full_name)
    try:
        photo_file_id, is_animated = (
            await get_profile_photo_file_id(client, entity_id) if entity_id else (None, False)
        )
        if photo_file_id:
            media_cls = InputMediaAnimation if is_animated else InputMediaPhoto
            await loading_message.edit_media(
                media=media_cls(media=photo_file_id, caption=response),
                reply_markup=buttons,
            )
        else:
            await loading_message.edit_text(response, reply_markup=buttons)
    except Exception as e:
        LOGGER.error(f"Error sending info for {entity_id}: {e}")
        await loading_message.edit_text(response, reply_markup=buttons)


def _divider() -> str:
    return "━━━━━━━━━━━━━━━━"


def display_name(first: str | None, last: str | None, fallback: str) -> str:
    """Имя без экранирования: для кнопок и copy_text."""
    name = f"{first or ''} {last or ''}".strip()
    return name or fallback


def _fragment_usernames(entity) -> str | None:
    names = [u.username for u in (getattr(entity, "usernames", None) or []) if getattr(u, "username", None)]
    return ", ".join(f"@{md_escape(n)}" for n in names) if names else None


def format_user_response(user, _=lambda x: x):
    full_name = display_name(getattr(user, "first_name", None), getattr(user, "last_name", None), _("unknown"))
    profile_type = _("bot_profile_info") if user.is_bot else _("user_profile_info")

    lines = [
        f"ℹ️ **{_('showing')} {profile_type}** 📋",
        _divider(),
        f"👤 **{_('full_name')}:** {md_escape(full_name)}",
    ]

    if user.username:
        lines.append(f"🔗 **{_('username_label')}:** @{md_escape(user.username)}")

    lines.append(f"🆔 **{_('user_id')}:** `{user.id}`")

    if not user.is_bot:
        premium = _("yes") if getattr(user, "is_premium", False) else _("no")
        lines.append(f"⭐ **{_('premium_user')}:** {premium}")

    lines.append(f"📍 **{_('data_center')}:** {get_dc_location(getattr(user, 'dc_id', 0), _)}")

    if not user.is_bot:
        creation_date = estimate_account_creation_date(user.id)
        lines.append(f"📅 **{_('created_on')}:** ~{creation_date.strftime('%B %Y')}")
        lines.append(f"⏳ **{_('account_age')}:** ~{calculate_account_age(creation_date, _)}")

    fragment = _fragment_usernames(user)
    if fragment:
        lines.append(f"🔹 **{_('fragment_usernames')}:** {fragment}")

    restricted = _("yes") if getattr(user, "is_restricted", False) else _("no")
    lines.append(f"🥶 **{_('account_frozen')}:** {restricted}")

    if not user.is_bot and getattr(user, "status", None) is not None:
        lines.append(f"🕒 **{_('last_seen')}:** {get_status_display(user.status, _)}")

    if getattr(user, "is_support", False):
        lines.append(f"👨‍💻 **{_('telegram_staff')}:** {_('yes')}")

    lines.extend([
        f"🌐 **{_('permanent_link')}:** 👉🏻 [{_('click_here')}](tg://user?id={user.id})",
        _divider(),
        f"👁 **{_('thank_you')}** ✅",
    ])

    return "\n".join(lines), full_name


def format_chat_response(chat, _=lambda x: x):
    chat_type_map = {
        ChatType.CHANNEL:    "chat_type_channel",
        ChatType.GROUP:      "chat_type_group",
        ChatType.SUPERGROUP: "chat_type_supergroup",
        ChatType.PRIVATE:    "chat_type_private",
    }
    chat_type = _(chat_type_map.get(chat.type, "unknown"))
    full_name = (getattr(chat, "title", None) or "").strip() or _("unnamed_chat")
    members = getattr(chat, "members_count", None)

    lines = [
        f"ℹ️ **{_('showing')} {chat_type} {_('profile_info')}** 📋",
        _divider(),
        f"👤 **{_('full_name')}:** {md_escape(full_name)}",
    ]

    if chat.username:
        lines.append(f"🔗 **{_('username_label')}:** @{md_escape(chat.username)}")

    lines.extend([
        f"🆔 **{_('chat_id')}:** `{chat.id}`",
        f"👥 **{_('total_members')}:** {members if members is not None else _('unknown')}",
        f"📍 **{_('data_center')}:** {get_dc_location(getattr(chat, 'dc_id', 0), _)}",
    ])

    fragment = _fragment_usernames(chat)
    if fragment:
        lines.append(f"🔹 **{_('fragment_usernames')}:** {fragment}")

    if chat.username:
        lines.append(f"🌐 **{_('permanent_link')}:** 👉🏻 [{_('click_here')}](https://t.me/{chat.username})")

    lines.extend([
        _divider(),
        f"👁 **{_('thank_you')}** ✅",
    ])

    return "\n".join(lines), full_name


def format_hidden_sender_response(sender_name: str, _=lambda x: x):
    sender_name = (sender_name or "").strip() or _("unknown")
    lines = [
        f"ℹ️ **{_('forwarded_user_info')}** 📋",
        _divider(),
        f"👤 **{_('name_label')}:** {md_escape(sender_name)}",
        _divider(),
        f"👁 **{_('thank_you')}** ✅",
    ]
    return "\n".join(lines), sender_name


async def describe_peer(client, chat, _):
    """Карточка для найденного чата: пользователь/бот или группа/канал."""
    if chat.type in (ChatType.PRIVATE, ChatType.BOT):
        user = await client.get_users(chat.id)
        return format_user_response(user, _)
    return format_chat_response(chat, _)
