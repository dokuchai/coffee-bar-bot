from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import date, timedelta, datetime, time
from aiogram_i18n import I18nContext

from filters import MagicI18nFilter
import database as db
import keyboards as kb
from states import UserSetup
from config import BotConfig
from database import get_now, get_today

router = Router()


# --- ПЕРВОНАЧАЛЬНАЯ НАСТРОЙКА РОЛЕЙ ---
@router.callback_query(UserSetup.waiting_for_role_selection, F.data.startswith("setup_toggle_role_"))
async def setup_toggle_role(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    role_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    selected_roles = data.get("selected_roles", [])

    if role_id in selected_roles:
        selected_roles.remove(role_id)
    else:
        selected_roles.append(role_id)

    await state.update_data(selected_roles=selected_roles)
    all_roles = await db.get_roles()
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_role_selection_keyboard(
            i18n=i18n,
            all_roles=all_roles,
            selected_role_ids=selected_roles,
            is_setup=True
        )
    )
    await callback.answer()


@router.callback_query(UserSetup.waiting_for_role_selection, F.data == "setup_finish_roles")
async def setup_finish_roles(callback: CallbackQuery, state: FSMContext, i18n: I18nContext, config: BotConfig):
    user_id = callback.from_user.id
    data = await state.get_data()
    selected_roles = data.get("selected_roles", [])

    if not selected_roles:
        await callback.answer(i18n.setup_error_no_roles(), show_alert=True)
        return

    await db.set_user_roles(user_id, selected_roles)
    await state.clear()

    is_admin = user_id in config.admin_ids
    await callback.message.edit_text(i18n.setup_success(), reply_markup=None)

    # ПРАВИЛЬНЫЙ ВЫЗОВ КЛАВИАТУРЫ
    main_kb = await kb.get_main_menu_keyboard(i18n, user_id, is_admin)
    await callback.message.answer(
        i18n.welcome(user_name=callback.from_user.first_name),
        reply_markup=main_kb
    )
    await callback.answer()


# --- ЛОГИКА СМЕНЫ (АВТОМАТИЧЕСКАЯ) ---

# handlers/user_handlers.py
@router.message(MagicI18nFilter("button_start_shift"))
async def handle_start(message: Message, i18n: I18nContext, config: BotConfig):
    user_id = message.from_user.id
    now = get_now()

    if now.time() < time(8, 30):
        await message.answer(i18n.error_too_early())
        return

    if await db.is_shift_active(user_id):
        await message.answer("🚫 У вас уже есть открытая смена!")
        return

    # Получаем все роли и уже использованные сегодня
    all_user_roles = await db.get_user_roles(user_id)
    used_role_ids = await db.get_used_role_ids_today(user_id)

    # Оставляем только те, которые еще не работали сегодня
    available_roles = [r for r in all_user_roles if r[0] not in used_role_ids]

    if not available_roles:
        await message.answer("✅ На сегодня все ваши должности отработаны!")
        return

    if len(available_roles) == 1:
        # Если осталась только одна роль — стартуем её без лишних вопросов
        role_id, role_name, _ = available_roles[0]
        await db.record_shift_start(user_id, role_id)
        is_admin = user_id in config.admin_ids
        reply_kb = await kb.get_main_menu_keyboard(i18n, user_id, is_admin)
        await message.answer(f"✅ Смена ({role_name}) открыта в {now.strftime('%H:%M')}", reply_markup=reply_kb)
    else:
        # Если несколько — даем выбор из ОСТАВШИХСЯ
        await message.answer(
            i18n.shift_select_role(),
            reply_markup=kb.get_role_selection_keyboard(
                i18n=i18n,
                all_roles=available_roles,
                prefix="start_with_role:"
            )
        )


# Хэндлер для выбора роли при старте
@router.callback_query(F.data.startswith("start_with_role:"))
async def process_role_choice(callback: CallbackQuery, i18n: I18nContext, config: BotConfig):
    role_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    # Проверяем еще раз статус (на случай двойного клика)
    if await db.is_shift_active(user_id):
        await callback.answer("Смена уже запущена!", show_alert=True)
        return

    await db.record_shift_start(user_id, role_id)

    # Получаем имя роли для сообщения
    all_roles = await db.get_roles()
    role_name = next((r[1] for r in all_roles if r[0] == role_id), "???")

    is_admin = user_id in config.admin_ids
    reply_kb = await kb.get_main_menu_keyboard(i18n, user_id, is_admin)

    await callback.message.edit_text(
        f"✅ Смена открыта!\n🎭 Должность: <b>{role_name}</b>\n⏰ Время: {get_now().strftime('%H:%M')}",
        reply_markup=None
    )
    # Чтобы обновить reply_keyboard внизу, нужно отправить новое сообщение
    await callback.message.answer("Используйте кнопки меню ниже для управления сменой.", reply_markup=reply_kb)
    await callback.answer()


@router.message(MagicI18nFilter("button_end_shift"))
async def handle_end(message: Message, i18n: I18nContext, config: BotConfig):
    user_id = message.from_user.id
    result = await db.close_shift(user_id)

    if result:
        mins, t_start, t_end = result

        if mins is None:
            await message.answer("❌ Активных смен не найдено.")
            return

    h, m = divmod(mins, 60)
    is_admin = user_id in config.admin_ids
    reply_kb = await kb.get_main_menu_keyboard(i18n, user_id, is_admin)
    await message.answer(
        f"🏁 Смена закрыта! Отработано: {h} ч. {m} м.\n"
        f"⏰ Время: <code>{t_start}</code> — <code>{t_end}</code>\n", reply_markup=reply_kb
    )


# --- СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ ---

@router.message(MagicI18nFilter("button_my_stats"))
async def show_stats_menu(message: Message, i18n: I18nContext):
    # Теперь передаем i18n, как требует keyboards.py
    await message.answer(
        "📅 За какой период показать статистику?",
        reply_markup=kb.get_user_stats_keyboard(i18n)
    )


@router.callback_query(F.data.startswith("usr_st:"))
async def process_user_stats(callback: CallbackQuery):
    period = callback.data.split(":")[1]
    user_id = callback.from_user.id
    today = get_today()

    if period == "week":
        start_date = today - timedelta(days=today.weekday())
        period_name = "неделю"
    else:
        start_date = today.replace(day=1)
        period_name = "месяц"

    # minutes (int), money (Decimal), shifts_list (List[str])
    minutes, money, shifts_list = await db.get_user_shifts_report(user_id, start_date, today)

    if not shifts_list:
        await callback.message.edit_text(f"❌ За {period_name} смен не найдено.")
        await callback.answer()
        return

    h, m = divmod(minutes, 60)
    report = [
        f"📊 <b>Статистика за {period_name}:</b>",
        f"⏱ Время: <b>{h} ч. {m} м.</b>",
        f"💰 Итого: <b>{money} RSD</b>",
        "---"
    ]
    report.extend(shifts_list)

    await callback.message.edit_text("\n".join(report))
    await callback.answer()


# --- СПРАВКА ---

@router.message(MagicI18nFilter("button_help"))
async def handle_help(message: Message, i18n: I18nContext):
    await message.answer(
        "📖 <b>Справка:</b>\n\n- Нажать 'Начать' можно с 08:30.\n- Если забудете закрыть, в 20:30 бот сделает это сам.")