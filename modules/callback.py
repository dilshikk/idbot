from pyrogram import Client, filters
from utils import LOGGER
from miscs.adbtn import get_admin_buttons
from miscs.mybtn import get_my_buttons
from miscs.startbtn import get_menu_buttons
from database import get_lang
from utils.i18n import get_translator, button_variants
from bot import bot


def button_filter(key: str):
    """Фильтр «пользователь нажал кнопку key» на любом из языков."""
    variants = button_variants(key)
    return filters.text & filters.create(
        lambda _, __, msg: bool(msg.text) and msg.text.strip() in variants
    )


def _chat_list_text(_) -> str:
    return (
        f"{_('chat_list_title')}\n\n"
        f"🔧 {_('welcome_how_to')}\n"
        f"1️⃣ {_('chat_list_step1')}\n"
        f"2️⃣ {_('welcome_step2')}"
    )


def _welcome_text(_) -> str:
    return (
        f"**{_('welcome_title')}**\n\n"
        f"**{_('welcome_how_to')}**\n"
        f"{_('welcome_step1')}\n"
        f"{_('welcome_step2')}\n\n"
        f"**{_('features_title')}**\n"
        f"{_('features_list')}\n\n"
        f"**{_('fetch_cta')}**"
    )


# Кнопки нижней клавиатуры работают только в личке:
# раньше любое сообщение «🔙 Назад» в группе вызывало ответ бота.
@bot.on_message(filters.private & button_filter("admin_button"))
async def admin_button_handler(client: Client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))
    LOGGER.info(f"Admins Chat button clicked by {user_id}")
    await message.reply_text(_chat_list_text(_), reply_markup=get_admin_buttons(user_id))


@bot.on_message(filters.private & button_filter("owner_button"))
async def owner_button_handler(client: Client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))
    LOGGER.info(f"Owner Chat button clicked by {user_id}")
    await message.reply_text(_chat_list_text(_), reply_markup=get_my_buttons(user_id))


@bot.on_message(filters.private & button_filter("back_button"))
async def back_button_handler(client: Client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id))
    LOGGER.info(f"Back button clicked by {user_id}")
    await message.reply_text(_welcome_text(_), reply_markup=get_menu_buttons(user_id))
