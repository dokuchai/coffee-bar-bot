# handlers/group_handlers.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram_i18n import I18nContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

router = Router()

# ❗️ Этот фильтр ловит ВСЕ сообщения в группах
# (и 'group', и 'supergroup')
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(CommandStart())
async def cmd_start_in_group(message: Message, i18n: I18nContext):
    """
    Этот хэндлер срабатывает на /start ТОЛЬКО в группах.
    """
    # Получаем базовую информацию о боте (чтобы создать ссылку)
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username

    # Создаем кнопку-ссылку, которая открывает ЛС с ботом
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=i18n.button_start_private(),  # ❗️ Новый ключ
            url=f"https://t.me/{bot_username}?start=from_group"
        )
    )

    await message.reply(
        i18n.group_welcome(user_name=message.from_user.first_name),
        reply_markup=builder.as_markup()
    )


@router.message()
async def any_message_in_group(message: Message, i18n: I18nContext):
    """
    Этот хэндлер ловит ЛЮБОЙ другой текст в группе
    (например, "Записать смену") и вежливо напоминает
    пользователю, что нужно делать.
    """

    # ❗️ Важно: Не реагируем на все подряд,
    # а только если кто-то пытается обратиться к боту по кнопке
    if message.text in [
        i18n.button_record_shift(locale="ru"),  # Проверяем рус. кнопку
        i18n.button_record_shift(locale="en"),  # Проверяем англ. кнопку
        i18n.button_my_stats(locale="ru"),
        i18n.button_my_stats(locale="en"),
        i18n.button_help(locale="ru"),
        i18n.button_help(locale="en")
    ]:
        await message.reply(i18n.group_please_go_to_private())