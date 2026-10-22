from pyrogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    RequestPeerTypeUser,
    RequestPeerTypeChannel,
    RequestPeerTypeChat,
)
from utils import LOGGER
from utils.i18n import get_translator
from database import get_lang

_REQUEST_DEFAULTS = dict(
    max=1,
    is_name_requested=True,
    is_username_requested=True,
    is_photo_requested=True,
)


def get_menu_buttons(user_id: int) -> ReplyKeyboardMarkup:
    lang = get_lang(user_id)
    _ = get_translator(lang)

    buttons = ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    _("menu_btn_user_info"),
                    request_user=RequestPeerTypeUser(button_id=1, is_bot=False, **_REQUEST_DEFAULTS),
                ),
            ],
            [
                KeyboardButton(
                    _("menu_btn_public_group"),
                    request_chat=RequestPeerTypeChat(button_id=7, is_username=True, **_REQUEST_DEFAULTS),
                ),
                KeyboardButton(
                    _("menu_btn_private_group"),
                    request_chat=RequestPeerTypeChat(button_id=6, is_username=False, **_REQUEST_DEFAULTS),
                ),
            ],
            [
                KeyboardButton(
                    _("menu_btn_public_channel"),
                    request_chat=RequestPeerTypeChannel(button_id=5, is_username=True, **_REQUEST_DEFAULTS),
                ),
                KeyboardButton(
                    _("menu_btn_private_channel"),
                    request_chat=RequestPeerTypeChannel(button_id=4, is_username=False, **_REQUEST_DEFAULTS),
                ),
            ],
            [
                KeyboardButton(
                    _("menu_btn_bot"),
                    request_user=RequestPeerTypeUser(button_id=2, is_bot=True, **_REQUEST_DEFAULTS),
                ),
                KeyboardButton(
                    _("menu_btn_premium"),
                    request_user=RequestPeerTypeUser(button_id=3, is_bot=False, is_premium=True, **_REQUEST_DEFAULTS),
                ),
            ],
            [
                KeyboardButton(_("admin_button")),
                KeyboardButton(_("owner_button")),
            ],
            [
                KeyboardButton(_("donate_button")),
                KeyboardButton(_("language_button")),
            ],
        ],
        resize_keyboard=True,
        placeholder=_("menu_placeholder"),
    )
    LOGGER.info(f"Menu buttons generated for lang={lang}")
    return buttons


LOGGER.info("Menu buttons module loaded successfully")
