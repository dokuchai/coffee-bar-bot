# handlers/common.py
from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, BotCommand, BotCommandScopeChat
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from typing import Callable

from filters import MagicI18nFilter

import database as db
import keyboards as kb
from config import BotConfig
from states import UserSetup

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, config: BotConfig, _: Callable):
    await state.clear()
    user_id = message.from_user.id

    await db.add_or_update_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    has_roles = await db.check_user_has_roles(user_id)

    if not has_roles:
        # Настройка ролей
        await state.set_state(UserSetup.waiting_for_role_selection)
        await state.update_data(selected_roles=[])
        all_roles = await db.get_roles()

        await message.answer(
            _("setup_welcome"),
            reply_markup=kb.get_role_selection_keyboard(
                i18n=_, all_roles=all_roles, is_setup=True
            )
        )
    else:
        # Главное меню
        is_admin = user_id in config.admin_ids
        await message.answer(
            _("welcome", user_name=message.from_user.first_name),
            reply_markup=await kb.get_main_menu_keyboard(_, user_id, is_admin)
        )


@router.message(Command("lang"))
async def cmd_lang(message: Message, _: Callable):
    await message.answer(
        _("select_language_text"),
        reply_markup=kb.get_language_keyboard()
    )


@router.callback_query(F.data.startswith("set_lang:"))
async def set_user_language(callback: CallbackQuery, _: Callable, config: BotConfig, bot: Bot):
    new_locale = callback.data.split(":")[1]
    user_id = callback.from_user.id

    # 1. Сохраняем в базу
    await db.set_user_locale(user_id, new_locale)

    # 2. Создаем временный переводчик для этого момента
    from middlewares.locales_manager import i18n as i18n_obj
    def _new(key, **kwargs):
        return i18n_obj.get(key, locale=new_locale, **kwargs)

    # 3. Обновляем синее меню команд ПЕРСОНАЛЬНО для этого юзера
    # Теперь даже если у него TG на английском, а он выбрал сербский — меню будет на сербском
    new_commands = [
        BotCommand(command="start", description=_new("menu_start")),
        BotCommand(command="help", description=_new("menu_help")),
        BotCommand(command="lang", description=_new("menu_lang"))
    ]
    await bot.set_my_commands(
        commands=new_commands,
        scope=BotCommandScopeChat(chat_id=user_id)
    )

    # 4. Редактируем сообщение с кнопками выбора языка
    await callback.message.edit_text(_new("language_changed_text"))

    # 5. Присылаем новое приветствие с НОВОЙ клавиатурой (Reply Keyboard)
    is_admin = user_id in config.admin_ids
    await callback.message.answer(
        _new("welcome", user_name=callback.from_user.first_name),
        reply_markup=await kb.get_main_menu_keyboard(_new, user_id, is_admin)
    )

    await callback.answer()


@router.message(Command("help"))
@router.message(MagicI18nFilter("button_help"))
async def cmd_help(message: Message, _: Callable, config: BotConfig):
    user_id = message.from_user.id

    # Обновляем данные (на случай, если юзер сменил имя в TG)
    await db.add_or_update_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    # Динамически собираем текст справки, передавая названия кнопок как переменные
    # Убедись, что в .ftl файле используются переменные типа {$btn_stats}
    help_text = _(
        "help_text",
        btn_start=_("button_start_shift"),
        btn_stats=_("button_my_stats"),
        btn_help="/help",
        btn_admin=_("button_admin_panel")
    )

    is_admin = user_id in config.admin_ids
    await message.answer(
        help_text,
        reply_markup=await kb.get_main_menu_keyboard(_, user_id, is_admin)
    )
