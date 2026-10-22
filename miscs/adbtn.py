from pyrogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    RequestPeerTypeChannel,
    RequestPeerTypeChat,
    ChatPrivileges,
)
from utils import LOGGER
from utils.i18n import get_translator
from database import get_lang

_COMMON_PRIVILEGES = dict(
    can_manage_chat=True,
    can_delete_messages=True,
    can_manage_video_chats=True,
    can_restrict_members=True,
    can_promote_members=True,
    can_change_info=True,
    can_invite_users=True,
    can_pin_messages=True,
    can_manage_topics=True,
)

_CHANNEL_EXTRA = dict(
    can_post_messages=True,
    can_edit_messages=True,
    can_post_stories=True,
    can_edit_stories=True,
    can_delete_stories=True,
)

_CHAT_REQUEST_DEFAULTS = dict(
    max=1,
    is_name_requested=True,
    is_username_requested=True,
    is_photo_requested=True,
)


def get_admin_buttons(user_id: int) -> ReplyKeyboardMarkup:
    lang = get_lang(user_id)
    _ = get_translator(lang)

    buttons = ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    _("admin_btn_channels"),
                    request_chat=RequestPeerTypeChannel(
                        button_id=10,
                        user_privileges=ChatPrivileges(**_COMMON_PRIVILEGES, **_CHANNEL_EXTRA),
                        **_CHAT_REQUEST_DEFAULTS,
                    ),
                ),
                KeyboardButton(
                    _("admin_btn_groups"),
                    request_chat=RequestPeerTypeChat(
                        button_id=11,
                        user_privileges=ChatPrivileges(**_COMMON_PRIVILEGES),
                        **_CHAT_REQUEST_DEFAULTS,
                    ),
                ),
            ],
            [KeyboardButton(_("back_button"))],
        ],
        resize_keyboard=True,
        placeholder=_("admin_placeholder"),
    )
    LOGGER.info(f"Admin buttons generated for lang={lang}")
    return buttons


LOGGER.info("Admin buttons module loaded successfully")
