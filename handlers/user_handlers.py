# handlers/user_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import date, timedelta, datetime, time
from aiogram_i18n import I18nContext

from filters import MagicI18nFilter
from aiogram.exceptions import TelegramBadRequest

import database as db
import keyboards as kb
from states import UserSetup, RecordShift
from config import BotConfig

router = Router()

# --- Обработка первоначальной настройки ролей ---
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
    data = await state.get_data()
    selected_roles = data.get("selected_roles", [])

    if not selected_roles:
        await callback.answer(i18n.setup_error_no_roles(), show_alert=True)
        return

    await db.set_user_roles(callback.from_user.id, selected_roles)
    await state.clear()

    is_admin = callback.from_user.id in config.admin_ids
    await callback.message.edit_text(
        i18n.setup_success(),
        reply_markup=None
    )
    await callback.message.answer(
        i18n.welcome(user_name=callback.from_user.first_name),
        reply_markup=kb.get_main_menu_keyboard(i18n, is_admin)
    )
    await callback.answer()

# --- НОВЫЙ ПРОЦЕСС ЗАПИСИ СМЕНЫ (ТВОЙ МЕТОД) ---
@router.message(MagicI18nFilter("button_record_shift"))
async def cmd_record_shift(message: Message, state: FSMContext, i18n: I18nContext):
    user_id = message.from_user.id
    # Проверка регистрации и ролей
    await db.add_or_update_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    user_roles = await db.get_user_roles(user_id)
    if not user_roles:
        await message.reply(i18n.error_no_roles_assigned())
        return

    # Проверяем, есть ли уже записанное НАЧАЛО смены
    recorded_start = await db.get_recorded_shift_start(user_id)

    if recorded_start:
        # Если НАЧАЛО есть -> Запрашиваем КОНЕЦ
        role_id, start_hour, start_date_obj = recorded_start
        # Проверяем, что пытаемся закрыть смену того же дня
        if start_date_obj != date.today():
            await db.delete_recorded_shift_start(user_id)
            # Пытаемся отправить сообщение, ловим KeyError на случай сломанного i18n
            try:
                await message.reply(i18n.shift_start_forgotten(start_date=start_date_obj.isoformat()))
            except KeyError:
                await message.reply("⚠️ Запись о начале смены за прошлый день удалена. Начните новую.")
            return

        await state.set_state(RecordShift.waiting_for_end_time)
        await state.update_data(role_id=role_id, start_hour=start_hour)
        await message.answer(
            i18n.shift_request_end_time(start_hour=start_hour),
            reply_markup=kb.get_end_time_keyboard()
        )
    else:
        # Если НАЧАЛА нет -> Запрашиваем РОЛЬ (если надо) и НАЧАЛО
        if len(user_roles) == 1:
            # Сразу запрашиваем НАЧАЛО
            role_id, role_name, _ = user_roles[0]
            await state.set_state(RecordShift.waiting_for_start_time)
            await state.update_data(role_id=role_id)
            await message.answer(
                i18n.shift_request_start_time_role(role_name=role_name),
                reply_markup=kb.get_start_time_keyboard()
            )
        else:
            # Сначала запрашиваем РОЛЬ
            await state.set_state(RecordShift.waiting_for_role)
            await message.answer(
                i18n.shift_select_role(),
                reply_markup=kb.get_role_selection_keyboard(
                    i18n=i18n, all_roles=user_roles, is_setup=False, prefix="record_shift_role_"
                )
            )

# Обработчик выбора РОЛИ для НАЧАЛА смены
@router.callback_query(RecordShift.waiting_for_role, F.data.startswith("record_shift_role_"))
async def process_shift_start_role(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    role_id = int(callback.data.split("_")[-1])
    all_roles = await db.get_roles()
    role_name = next((name for r_id, name, _ in all_roles if r_id == role_id), "???")

    await state.set_state(RecordShift.waiting_for_start_time)
    await state.update_data(role_id=role_id)

    await callback.message.edit_text(
        i18n.shift_request_start_time_role(role_name=role_name),
        reply_markup=kb.get_start_time_keyboard()
    )
    await callback.answer()

# Обработчик выбора часа НАЧАЛА смены
@router.callback_query(RecordShift.waiting_for_start_time, F.data.startswith("start_"))
async def process_shift_start_time(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    start_hour = int(callback.data.split("_")[1])
    data = await state.get_data()
    role_id = data.get("role_id")
    user_id = callback.from_user.id

    if not role_id:
        # Обернем в try-except
        try:
            await callback.message.edit_text(i18n.error_role_or_time_not_found())
        except KeyError:
             await callback.message.edit_text("🚫 Ошибка: Не найдены данные. Попробуйте снова.", reply_markup=None)
        await state.clear(); await callback.answer(); return

    # Проверяем пересечение с уже ЗАПИСАННЫМИ сменами за СЕГОДНЯ
    today = date.today()
    existing_shifts = await db.get_user_shifts_for_day(user_id, today)
    for old_start, old_end in existing_shifts:
        # Новое начало не должно попадать внутрь или начинаться до конца предыдущей
        # start_hour >= old_end
        if start_hour < old_end:
            try:
                await callback.message.edit_text(
                    i18n.shift_error_start_overlap(
                        start_hour=start_hour, old_start=old_start, old_end=old_end
                    ))
            except KeyError:
                await callback.message.edit_text(
                    f"🚫 Ошибка! Время начала ({start_hour}:00) пересекается с ({old_start}:00 - {old_end}:00).",
                    reply_markup=None
                )
            await state.clear(); await callback.answer(i18n.shift_error_alert(), show_alert=True); return

    # Все ок, записываем НАЧАЛО в active_shifts
    try:
        await db.record_shift_start(user_id, role_id, start_hour)
        await callback.message.edit_text(i18n.shift_start_recorded(start_hour=start_hour))
    except KeyError as e:
         await callback.message.edit_text(
            f"ОШИБКА i18n ({e})\nНачало смены в {start_hour}:00 записано.",
            reply_markup=None
         )
    except Exception as e:
        try:
            await callback.message.edit_text(i18n.generic_db_error(error=str(e)))
        except KeyError:
            await callback.message.edit_text(f"Ошибка БД: {e}", reply_markup=None)


    await state.clear()
    await callback.answer()

# Обработчик выбора часа ОКОНЧАНИЯ смены
@router.callback_query(RecordShift.waiting_for_end_time, F.data.startswith("end_"))
async def process_shift_end_time(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    end_hour = int(callback.data.split("_")[1])
    data = await state.get_data()
    start_hour = data.get("start_hour")
    role_id = data.get("role_id")
    user_id = callback.from_user.id

    if role_id is None or start_hour is None:
        try:
            await callback.message.edit_text(i18n.error_role_or_time_not_found())
        except KeyError:
            await callback.message.edit_text("🚫 Ошибка: Не найдены данные. Попробуйте снова.", reply_markup=None)
        await state.clear(); await callback.answer(i18n.shift_error_alert(), show_alert=True); return

    # Валидация 1: Конец > Начало
    if end_hour <= start_hour:
        # Используем answer с show_alert=True
        await callback.answer(i18n.shift_error_end_lt_start(end_hour=end_hour, start_hour=start_hour), show_alert=True)
        return # Не сбрасываем состояние

    # Валидация 2: Пересечение с ЗАПИСАННЫМИ сменами за СЕГОДНЯ
    today = date.today()
    existing_shifts = await db.get_user_shifts_for_day(user_id, today)
    for old_start, old_end in existing_shifts:
        if (start_hour < old_end and end_hour > old_start):
            try:
                await callback.message.edit_text(i18n.shift_error_overlap(
                    new_start=start_hour, new_end=end_hour, old_start=old_start, old_end=old_end
                ))
            except KeyError:
                await callback.message.edit_text(
                    f"🚫 Ошибка! Смена ({start_hour}:00 - {end_hour}:00) пересекается с ({old_start}:00 - {old_end}:00).",
                    reply_markup=None
                    )
            await db.delete_recorded_shift_start(user_id) # Удаляем ошибочное начало
            await state.clear(); await callback.answer(i18n.shift_error_alert(), show_alert=True); return

    # Все ок, сохраняем ЗАВЕРШЕННУЮ смену и удаляем начало
    try:
        await db.add_shift(user_id, role_id, start_hour, end_hour)
        await db.delete_recorded_shift_start(user_id)

        hours_worked = end_hour - start_hour
        all_roles = await db.get_roles()
        role_name = next((name for r_id, name, _ in all_roles if r_id == role_id), "???")

        await callback.message.edit_text(
            i18n.shift_success_recorded(
                date=today.isoformat(), role_name=role_name,
                start_time=start_hour, end_time=end_hour, hours=hours_worked
            )
        )
    except KeyError as e:
         await callback.message.edit_text(
             f"ОШИБКА i18n ({e})\nСмена {start_hour}:00 - {end_hour}:00 записана.",
             reply_markup=None
         )
    except Exception as e:
        try:
            await callback.message.edit_text(i18n.generic_db_error(error=str(e)))
        except KeyError:
            await callback.message.edit_text(f"Ошибка БД: {e}", reply_markup=None)
        try: await db.delete_recorded_shift_start(user_id)
        except: pass

    await state.clear()
    await callback.answer()

# --- Статистика ---
@router.message(MagicI18nFilter("button_my_stats"))
async def my_statistics(message: Message, i18n: I18nContext, config: BotConfig):
     user_id=message.from_user.id
     await db.add_or_update_user(user_id=user_id,username=message.from_user.username,first_name=message.from_user.first_name)
     await message.answer(i18n.stats_select_period(), reply_markup=kb.get_stats_period_keyboard(i18n))

@router.callback_query(F.data.startswith("stats_"))
async def send_my_stats_report(callback: CallbackQuery, i18n: I18nContext):
    period = callback.data.split("_")[1]; user_id = callback.from_user.id; today = date.today()
    if period == "week": start_date=today-timedelta(days=today.weekday()); end_date=today
    elif period == "month": start_date=today.replace(day=1); end_date=today
    else: await callback.answer("Unknown period", show_alert=True); return

    total_hours, total_earnings, report_by_role = await db.get_user_shifts_report(user_id, start_date, end_date)
    if not report_by_role:
        await callback.message.edit_text(i18n.stats_report_no_data())
        await callback.answer()
        return

    report_lines = []
    try:
        report_lines.append(i18n.stats_report_header(start_date=start_date.isoformat(), end_date=end_date.isoformat()))
        for role_name, data in report_by_role.items():
            report_lines.append(f"\n{i18n.stats_role_header(role_name=role_name, hours=data['hours'], rate=data['rate'], earnings=data['earnings'])}")
            report_lines.extend(data['shifts'])
        report_lines.append(f"\n\n{i18n.stats_report_footer_total(total_hours=total_hours, total_earnings=total_earnings)}")
        await callback.message.edit_text("\n".join(report_lines), disable_web_page_preview=True)
    except KeyError as e:
        # Запасной вариант без i18n
        await callback.message.edit_text(
            f"ОШИБКА i18n ({e}).\nОтчет {start_date.isoformat()}-{end_date.isoformat()}.\n"
            f"Итого: {total_hours} ч., {total_earnings} RSD.\n"
            f"Детали (сырые): {report_by_role}",
            parse_mode=None, disable_web_page_preview=True
        )
    await callback.answer()