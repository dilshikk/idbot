from pyrogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    RequestPeerTypeChannel,
    RequestPeerTypeChat,
)
from utils import LOGGER
from utils.i18n import get_translator
from database import get_lang

_OWNER_REQUEST_DEFAULTS = dict(
    is_creator=True,
    max=1,
    is_name_requested=True,
    is_username_requested=True,
    is_photo_requested=True,
)


def get_my_buttons(user_id: int) -> ReplyKeyboardMarkup:
    lang = get_lang(user_id)
    _ = get_translator(lang)

    buttons = ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    _("my_btn_channel"),
                    request_chat=RequestPeerTypeChannel(button_id=9, **_OWNER_REQUEST_DEFAULTS),
                ),
                KeyboardButton(
                    _("my_btn_group"),
                    request_chat=RequestPeerTypeChat(button_id=8, **_OWNER_REQUEST_DEFAULTS),
                ),
            ],
            [KeyboardButton(_("back_button"))],
        ],
        resize_keyboard=True,
        placeholder=_("my_placeholder"),
    )
    LOGGER.info(f"My buttons generated for lang={lang}")
    return buttons


LOGGER.info("My buttons module loaded successfully")
