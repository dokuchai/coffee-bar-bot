# handlers/group_handlers.py
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Callable, Any

router = Router()

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
async def any_message_in_group(message: Message, _: Callable, i18n: Any):
    """
    Ловит нажатия кнопок (текстовые сообщения) в группе и отправляет в личку.
    """
    if not message.text:
        return

    # Список ключей кнопок, на которые бот должен реагировать в группе
    button_keys = [
        "button_start_shift",
        "button_end_shift",
        "button_my_stats",
        "button_help"
    ]

    # Собираем все варианты текста кнопок на всех языках
    forbidden_texts = []
    for lang in ["ru", "sr", "en"]:
        for key in button_keys:
            forbidden_texts.append(i18n.get(key, locale=lang))

    # Если текст сообщения совпадает с любой кнопкой на любом языке
    if message.text in forbidden_texts:
        await message.reply(_("group_please_go_to_private"))