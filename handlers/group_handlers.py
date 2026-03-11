# handlers/group_handlers.py
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Callable

from middlewares.locales_manager import i18n as i18n_obj

router = Router()

_BUTTON_KEYS = ["button_start_shift", "button_end_shift", "button_my_stats", "button_help"]
_BUTTON_TEXTS = frozenset(
    i18n_obj.get(key, locale=lang)
    for lang in ["ru", "sr", "en"]
    for key in _BUTTON_KEYS
)

# Этот фильтр ловит ВСЕ сообщения в группах
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(CommandStart())
async def cmd_start_in_group(message: Message, _: Callable):
    """
    Срабатывает на /start ТОЛЬКО в группах.
    """
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=_("button_start_private"),  # Используем функцию перевода
            url=f"https://t.me/{bot_username}?start=from_group"
        )
    )

    await message.reply(
        _("group_welcome", user_name=message.from_user.first_name),
        reply_markup=builder.as_markup()
    )

@router.message()
async def any_message_in_group(message: Message, _: Callable):
    """
    Ловит нажатия кнопок (текстовые сообщения) в группе и отправляет в личку.
    """
    if not message.text:
        return

    if message.text in _BUTTON_TEXTS:
        await message.reply(_("group_please_go_to_private"))