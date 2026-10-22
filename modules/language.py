from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import bot
from utils import LOGGER
from database import get_lang, set_lang
from config import COMMAND_PREFIX
from miscs.startbtn import get_menu_buttons
from utils.i18n import get_translator, load_translations

LANGUAGES = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "uz": "🇺🇿 Oʻzbekcha",
}


def _get_all_lang_button_variants() -> set:
    variants = set()
    for lang in LANGUAGES:
        t = load_translations(lang)
        if "language_button" in t:
            variants.add(t["language_button"])
    return variants


@bot.on_message(
    filters.command(["language", "lang"], prefixes=COMMAND_PREFIX.split("|"))
    | filters.text & filters.create(
        lambda _, __, msg: msg.text and msg.text.strip() in _get_all_lang_button_variants()
    )
)
async def choose_language(bot: Client, message):
    if not message.from_user:
        await message.delete()
        return

    user_id = message.from_user.id
    _ = get_translator(get_lang(user_id) or "ru")

    keyboard = [
        [InlineKeyboardButton(text=name, callback_data=f"set_lang:{code}")]
        for code, name in LANGUAGES.items()
    ]
    await message.reply_text(
        _("choose_language"),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    LOGGER.info(f"Language menu opened for user {user_id}")


@bot.on_callback_query(filters.regex(r"^set_lang:(\w+)$"))
async def set_user_language(bot: Client, query):
    if not query.from_user:
        return

    user_id = query.from_user.id
    lang_code = query.data.split(":")[1]

    if lang_code not in LANGUAGES:
        await query.answer(_("invalid_language"), show_alert=True)
        return

    set_lang(user_id, lang_code)
    _ = get_translator(lang_code)

    await query.message.edit_text(
        f"**{_('language_set')}**\n\n**{LANGUAGES[lang_code]}**"
    )
    await bot.send_message(
        chat_id=user_id,
        text=f"**{_('welcome_title')}**\n\n{_('fetch_cta')}",
        reply_markup=get_menu_buttons(user_id),
    )
    LOGGER.info(f"✅ User {user_id} changed language to {lang_code}")
