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
    """Главное меню: только 4 основных действия и «Настройки».
    Группы и каналы больше не делятся на публичные и приватные:
    Telegram сам покажет все подходящие чаты в одном списке."""
    _ = get_translator(get_lang(user_id))

    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    _("menu_btn_user"),
                    request_user=RequestPeerTypeUser(button_id=1, is_bot=False, **_REQUEST_DEFAULTS),
                ),
                KeyboardButton(
                    _("menu_btn_bot"),
                    request_user=RequestPeerTypeUser(button_id=2, is_bot=True, **_REQUEST_DEFAULTS),
                ),
            ],
            [
                KeyboardButton(
                    _("menu_btn_group"),
                    request_chat=RequestPeerTypeChat(button_id=6, **_REQUEST_DEFAULTS),
                ),
                KeyboardButton(
                    _("menu_btn_channel"),
                    request_chat=RequestPeerTypeChannel(button_id=4, **_REQUEST_DEFAULTS),
                ),
            ],
            [KeyboardButton(_("settings_button"))],
        ],
        resize_keyboard=True,
        placeholder=_("menu_placeholder"),
    )


def get_settings_buttons(user_id: int) -> ReplyKeyboardMarkup:
    """Подменю «Настройки»: всё второстепенное собрано здесь."""
    _ = get_translator(get_lang(user_id))

    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(_("admin_button")), KeyboardButton(_("owner_button"))],
            [KeyboardButton(_("donate_button")), KeyboardButton(_("language_button"))],
            [KeyboardButton(_("help_button"))],
            [KeyboardButton(_("back_button"))],
        ],
        resize_keyboard=True,
        placeholder=_("settings_placeholder"),
    )


LOGGER.info("Menu buttons module loaded successfully")
