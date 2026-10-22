from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pyrogram.enums import ChatType, UserStatus
from utils import LOGGER

# У Telegram ровно 5 продакшн дата-центров.
# DC1 и DC3 находятся в Майами, DC2 и DC4 в Амстердаме, DC5 в Сингапуре.
DC_LOCATIONS = {
    1: "MIA, Miami, USA, US",
    2: "AMS, Amsterdam, Netherlands, NL",
    3: "MIA, Miami, USA, US",
    4: "AMS, Amsterdam, Netherlands, NL",
    5: "SIN, Singapore, SG",
}


def calculate_account_age(creation_date, _=lambda x: x):
    delta = relativedelta(datetime.now(), creation_date)
    return (
        f"{delta.years} {_('years')}, "
        f"{delta.months} {_('months')}, "
        f"{delta.days} {_('days')}"
    )


def estimate_account_creation_date(user_id: int) -> datetime:
    reference_points = [
        (100000000,  datetime(2013, 8, 1)),
        (1273841502, datetime(2020, 8, 13)),
        (1500000000, datetime(2021, 5, 1)),
        (2000000000, datetime(2022, 12, 1)),
    ]
    closest_id, closest_date = min(reference_points, key=lambda x: abs(x[0] - user_id))
    return closest_date + timedelta(days=(user_id - closest_id) / 20_000_000)


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


def _divider() -> str:
    return "━━━━━━━━━━━━━━━━"


def format_user_response(user, is_group_context=False, chat=None, _=lambda x: x):
    full_name = f"{getattr(user, 'first_name', _('unknown'))} {getattr(user, 'last_name', '')}".strip()
    profile_type = _("bot_profile_info") if user.is_bot else _("user_profile_info")
    creation_date = estimate_account_creation_date(user.id)

    lines = [
        f"ℹ️ **{_('showing')} {profile_type}** 📋",
        _divider(),
        f"👤 **{_('full_name')}:** {full_name}",
    ]

    if user.username:
        lines.append(f"🔗 **{_('username_label')}:** @{user.username}")

    lines.append(f"🆔 **{_('user_id')}:** `{user.id}`")

    if is_group_context and chat:
        lines.append(f"💬 **{_('chat_id')}:** `{chat.id}`")

    if not user.is_bot:
        premium = _("yes") if getattr(user, "is_premium", False) else _("no")
        lines.append(f"⭐ **{_('premium_user')}:** {premium}")

    lines.append(f"📍 **{_('data_center')}:** {get_dc_location(getattr(user, 'dc_id', 0), _)}")

    if not user.is_bot:
        lines.append(f"📅 **{_('created_on')}:** {creation_date.strftime('%B %d, %Y')}")
        lines.append(f"⏳ **{_('account_age')}:** {calculate_account_age(creation_date, _)}")

    if hasattr(user, "usernames") and user.usernames:
        usernames = ", ".join(f"@{u.username}" for u in user.usernames)
        lines.append(f"🔹 **{_('fragment_usernames')}:** {usernames}")

    restricted = _("yes") if getattr(user, "is_restricted", False) else _("no")
    lines.append(f"🥶 **{_('account_frozen')}:** {restricted}")

    if not user.is_bot and hasattr(user, "status"):
        lines.append(f"🕒 **{_('last_seen')}:** {get_status_display(user.status, _)}")

    if getattr(user, "is_support", False):
        lines.append(f"👨‍💻 **{_('telegram_staff')}:** {_('yes')}")

    lines.extend([
        f"🌐 **{_('permanent_link')}:** 👉🏻 [{_('click_here')}](tg://user?id={user.id})",
        _divider(),
        f"👁 **{_('thank_you')}** ✅",
    ])

    return "\n".join(lines), full_name


format_user_response_resolve = format_user_response


def format_chat_response(chat, _=lambda x: x):
    chat_type_map = {
        ChatType.CHANNEL:    "chat_type_channel",
        ChatType.GROUP:      "chat_type_group",
        ChatType.SUPERGROUP: "chat_type_supergroup",
        ChatType.PRIVATE:    "chat_type_private",
    }
    chat_type = _(chat_type_map.get(chat.type, "unknown"))
    full_name = getattr(chat, "title", _("unnamed_chat"))

    lines = [
        f"ℹ️ **{_('showing')} {chat_type} {_('profile_info')}** 📋",
        _divider(),
        f"👤 **{_('full_name')}:** {full_name}",
    ]

    if chat.username:
        lines.append(f"🔗 **{_('username_label')}:** @{chat.username}")

    lines.extend([
        f"🆔 **{_('chat_id')}:** `{chat.id}`",
        f"👥 **{_('total_members')}:** {getattr(chat, 'members_count', _('unknown'))}",
        f"📍 **{_('data_center')}:** {get_dc_location(getattr(chat, 'dc_id', 0), _)}",
    ])

    if hasattr(chat, "usernames") and chat.usernames:
        usernames = ", ".join(f"@{u.username}" for u in chat.usernames)
        lines.append(f"🔹 **{_('fragment_usernames')}:** {usernames}")

    if chat.username:
        lines.append(f"🌐 **{_('permanent_link')}:** 👉🏻 [{_('click_here')}](tg://resolve?domain={chat.username})")

    lines.extend([
        _divider(),
        f"👁 **{_('thank_you')}** ✅",
    ])

    return "\n".join(lines), full_name


format_chat_response_resolve = format_chat_response


def format_hidden_sender_response(sender_name: str, _=lambda x: x):
    lines = [
        f"ℹ️ **{_('forwarded_user_info')}** 📋",
        _divider(),
        f"👤 **{_('name_label')}:** {sender_name}",
        _divider(),
        f"👁 **{_('thank_you')}** ✅",
    ]
    return "\n".join(lines), sender_name
