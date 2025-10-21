# handlers/admin_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import date, datetime, timedelta
from aiogram_i18n import I18nContext
from typing import Optional # Добавим Optional

from filters import MagicI18nFilter
from aiogram.exceptions import TelegramBadRequest # Важно импортировать

import database as db
import keyboards as kb
from states import AdminManualAdd, AdminDeleteUser
from config import MAX_DAILY_HOURS, BotConfig

router = Router()

# --- Главное меню админа ---
@router.message(MagicI18nFilter("button_admin_panel"))
async def admin_panel(message: Message, i18n: I18nContext, config: BotConfig):
    user_id = message.from_user.id
    await db.add_or_update_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    try:
        await message.answer(
            i18n.admin_panel_welcome(),
            reply_markup=kb.get_admin_panel_keyboard(i18n)
        )
    except KeyError as e:
        await message.answer(
            f"ОШИБКА i18n (ключ не найден: {e}).",
            parse_mode=None
        )

# --- Отчеты (День/Неделя/Месяц) ---
@router.callback_query(F.data.startswith("admin_report_"))
async def show_summary_report(callback: CallbackQuery, i18n: I18nContext):
    """
    Формирует и отправляет общий отчет по ВСЕМ сотрудникам, с разбивкой по ролям.
    Отчет за день учитывает ТОЛЬКО 'auto' записи.
    """
    period = callback.data.split("_")[-1]
    today = date.today()
    header_key = "admin_summary_report_header" # Ключ с подчеркиванием
    header_args = {}
    entry_types_filter: Optional[list[str]] = None # Используем Optional
    start_date: date = today # Инициализация
    end_date: date = today   # Инициализация

    if period == "day":
        start_date = today
        end_date = today
        header_key = "admin_summary_report_header_day" # Ключ с подчеркиванием
        header_args = {"date": today.isoformat()}
        entry_types_filter = ['auto']
    elif period == "week":
        start_date = today - timedelta(days=today.weekday())
        end_date = today
        header_args = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
    elif period == "month":
        start_date = today.replace(day=1)
        end_date = today
        header_args = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
    else:
        await callback.answer("Error period", show_alert=True)
        return

    summary_data = await db.get_summary_report(start_date, end_date, entry_types=entry_types_filter)

    try:
        if not summary_data:
            try:
                await callback.message.edit_text(i18n.admin_summary_report_no_data())
            except KeyError as e_inner:
                await callback.message.edit_text(f"ОШИБКА i18n ({e_inner}). Нет данных.", parse_mode=None)
            await callback.answer()
            return

        report_lines = []
        grand_total_hours_all = 0.0
        grand_total_earnings_all = 0.0

        # Получаем перевод заголовка
        header = i18n.get(header_key, **header_args)
        report_lines.append(header)

        # Формируем строки отчета
        for i, user_data in enumerate(summary_data, 1):
            user_name = user_data['user_name']
            total_hours = user_data['total_hours']
            total_earnings = user_data['total_earnings']

            grand_total_hours_all += total_hours
            grand_total_earnings_all += total_earnings

            user_line = i18n.admin_summary_user_line(
                num=i,
                user_name=user_name,
                total_hours=total_hours,
                total_earnings=total_earnings
            )
            report_lines.append(f"\n{user_line}")

            for role_name, role_data in user_data['roles'].items():
                role_line = i18n.admin_summary_role_line(
                    role_name=role_name or "??",
                    hours=role_data['hours'],
                    earnings=role_data['earnings']
                )
                report_lines.append(f"  {role_line}")

        # Формируем итоговую строку
        footer = i18n.admin_summary_report_footer_grand_total(
            grand_total_hours=round(grand_total_hours_all, 2),
            grand_total_earnings=round(grand_total_earnings_all, 2)
        )
        report_lines.append(f"\n\n{footer}")

        # Отправляем отчет (оставляем HTML)
        await callback.message.edit_text("\n".join(report_lines))

    except KeyError as e:
        # Ошибка i18n - отправляем без HTML
        await callback.message.edit_text(
            f"ОШИБКА i18n (ключ не найден: {e}).\n"
            f"Отчет с {start_date.isoformat()} по {end_date.isoformat()}.\n"
            "Данные (сырые):\n"
            f"{summary_data}",
            parse_mode=None
        )
    except TelegramBadRequest as e_html:
        # Ошибка HTML - отправляем без HTML
        await callback.message.edit_text(
            f"ОШИБКА HTML (не могу отправить): {e_html}\n"
            f"Отчет с {start_date.isoformat()} по {end_date.isoformat()}.\n"
            "Данные (сырые):\n"
            f"{summary_data}",
            parse_mode=None
        )
    await callback.answer()


# --- Ручная корректировка ---
@router.callback_query(F.data == "admin_manual_add")
async def start_manual_add(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    users = await db.get_all_users()
    try:
        if not users:
            await callback.message.edit_text(i18n.admin_no_users_in_db())
            await callback.answer()
            return
        await state.set_state(AdminManualAdd.waiting_for_user)
        await callback.message.edit_text(
            i18n.admin_select_user_adjust(),
            reply_markup=kb.get_user_selection_keyboard(users, prefix="manual_user")
        )
    except KeyError as e:
        await callback.message.edit_text(f"ОШИБКА i18n ({e})", parse_mode=None)
    await callback.answer()

@router.callback_query(AdminManualAdd.waiting_for_user, F.data.startswith("manual_user_"))
async def manual_add_user_selected(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    user_id_to_add = int(callback.data.split("_")[-1])
    user_name = next((name for uid, name in await db.get_all_users() if uid == user_id_to_add), "???")
    await state.update_data(user_id=user_id_to_add, user_name=user_name)
    user_roles = await db.get_user_roles(user_id_to_add)

    if not user_roles:
        try:
            await callback.message.edit_text(i18n.error_user_has_no_roles_admin())
        except KeyError:
            await callback.message.edit_text("Ошибка: У юзера нет ролей.", parse_mode=None)
        await state.clear()
        await callback.answer()
        return

    if len(user_roles) == 1:
        role_id, role_name, _ = user_roles[0]
        await state.update_data(role_id=role_id)
        await state.set_state(AdminManualAdd.waiting_for_hours)
        try:
            await callback.message.edit_text(
                i18n.adjust_user_selected_single_role(
                    user_name=user_name, user_id=user_id_to_add, role_name=role_name
                )
            )
        except KeyError as e:
            await callback.message.edit_text(
                f"ОШИБКА i18n ({e}).\nВыбран {user_name} ({role_name}). Введите часы:",
                parse_mode=None
            )
    else:
        await state.set_state(AdminManualAdd.waiting_for_role)
        try:
            await callback.message.edit_text(
                i18n.adjust_select_role(user_name=user_name),
                reply_markup=kb.get_role_selection_keyboard(
                    i18n=i18n, all_roles=user_roles, is_setup=False, prefix="adjust_role_"
                )
            )
        except KeyError as e:
            await callback.message.edit_text(
                f"ОШИБКА i18n ({e}).\nВыбран {user_name}. Выберите роль:",
                reply_markup=kb.get_role_selection_keyboard(
                    i18n=i18n, all_roles=user_roles, is_setup=False, prefix="adjust_role_"
                ),
                parse_mode=None
            )
    await callback.answer()

@router.callback_query(AdminManualAdd.waiting_for_role, F.data.startswith("adjust_role_"))
async def manual_add_role_selected(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    role_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    user_name = data.get("user_name", "???")
    user_id = data.get("user_id")

    all_roles = await db.get_roles()
    role_name = next((name for r_id, name, _ in all_roles if r_id == role_id), "???")
    await state.update_data(role_id=role_id)
    await state.set_state(AdminManualAdd.waiting_for_hours)

    try:
        await callback.message.edit_text(
            i18n.adjust_user_selected_multi_role(
                user_name=user_name, user_id=user_id, role_name=role_name
            )
        )
    except KeyError as e:
        await callback.message.edit_text(
            f"ОШИБКА i18n ({e}).\nВыбран {user_name} ({role_name}). Введите часы:",
            parse_mode=None
        )
    await callback.answer()

@router.message(AdminManualAdd.waiting_for_hours)
async def manual_add_hours_entered(message: Message, state: FSMContext, i18n: I18nContext):
    try:
        hours_to_add = float(message.text.strip().replace(',', '.'))
        if hours_to_add == 0:
            raise ValueError("Часы не могут быть 0")
    except (ValueError, AssertionError):
        try:
            # Ошибка формата - можно без HTML
            await message.answer(i18n.adjust_error_format(), parse_mode=None)
        except KeyError:
            await message.answer("Ошибка: Неверный формат.", parse_mode=None)
        return

    data = await state.get_data()
    user_id = data.get("user_id")
    user_name = data.get("user_name", "???")
    role_id = data.get("role_id")

    if not role_id:
        try:
            # Ошибка - можно без HTML
            await message.answer(i18n.error_role_not_found_in_state_admin(), parse_mode=None)
        except KeyError:
            await message.answer("Ошибка: Не найдена роль.", parse_mode=None)
        await state.clear()
        return

    today = date.today()
    days_passed_this_month = today.day
    max_h_overall = days_passed_this_month * MAX_DAILY_HOURS
    month_start_date = today.replace(day=1)

    current_h_overall = await db.get_month_hours_for_user(user_id, month_start_date)
    new_total_overall = current_h_overall + hours_to_add

    current_h_role: float = 0.0
    new_total_role: float = 0.0
    all_roles = await db.get_roles()
    role_name = next((name for r_id, name, _ in all_roles if r_id == role_id), "???")

    # --- Валидации ---
    validation_error_key: Optional[str] = None
    validation_error_args: dict = {}
    validation_error_fallback_text: Optional[str] = None # Запасной текст без HTML

    # Валидация: Отрицательный баланс по РОЛИ
    if hours_to_add < 0:
        current_h_role = await db.get_month_hours_for_user_role(user_id, role_id, month_start_date)
        new_total_role = current_h_role + hours_to_add
        if new_total_role < 0:
            validation_error_key = "adjust_error_negative_role_limit"
            validation_error_args = {
                "hours_to_add": hours_to_add, "role_name": role_name,
                "current_hours": current_h_role, "new_total": new_total_role
            }
            validation_error_fallback_text = (
                f"🚫 Нельзя вычесть {hours_to_add} ч. для роли '{role_name}'.\n"
                f"Итог роли: {current_h_role} ч. -> {new_total_role} ч. (< 0)"
            )

    # Валидация: Общий отрицательный баланс (если ролевая прошла)
    if not validation_error_key and hours_to_add < 0 and new_total_overall < 0:
        validation_error_key = "adjust_error_negative_limit"
        validation_error_args = {
            "hours_to_add": hours_to_add, "current_hours": current_h_overall, "new_total": new_total_overall
        }
        validation_error_fallback_text = (
            f"🚫 Нельзя вычесть столько часов.\n"
            f"Общий итог: {current_h_overall} ч. -> {new_total_overall} ч. (< 0)"
        )

    # Валидация: Общий положительный лимит (если отрицательные прошли)
    if not validation_error_key and hours_to_add > 0 and new_total_overall > max_h_overall:
        validation_error_key = "adjust_error_positive_limit"
        validation_error_args = {
            "hours_to_add": hours_to_add, "month": today.strftime('%Y-%m'),
            "current_hours": current_h_overall, "new_total": new_total_overall,
            "today": today.isoformat(), "max_hours": max_h_overall
        }
        validation_error_fallback_text = (
            f"🚫 Превышен лимит месяца.\n"
            f"Нельзя добавить {hours_to_add} ч.\n"
            f"Общий итог: {current_h_overall} ч. -> {new_total_overall} ч."
        )

    # --- Отправка сообщения об ошибке валидации (если была) ---
    if validation_error_key:
        try:
            # Пытаемся отправить с HTML
            await message.answer(i18n.get(validation_error_key, **validation_error_args))
        except (KeyError, TelegramBadRequest):
            # Если не вышло - отправляем без HTML
            if validation_error_fallback_text:
                 await message.answer(validation_error_fallback_text, parse_mode=None)
            else: # На всякий случай
                 await message.answer("🚫 Ошибка валидации.", parse_mode=None)
        await state.clear()
        return # Важно прервать

    # --- Если валидации пройдены -> Сохранение ---
    try:
        shift_date_str = today.isoformat()
        await db.add_manual_shift(user_id, role_id, shift_date_str, hours_to_add)
        hours_str = f"+{hours_to_add}" if hours_to_add > 0 else str(hours_to_add)
        # role_name уже есть
        await message.answer(
            i18n.adjust_success_with_role( # HTML для успеха
                user_name=user_name, date=shift_date_str, hours_str=hours_str, role_name=role_name
            )
        )
    except TelegramBadRequest as e: # Ошибка HTML в success-сообщении
        await message.answer(f"ОШИБКА HTML ({e})\nНо часы были сохранены.", parse_mode=None)
    except KeyError as e: # Ошибка i18n в success-сообщении
        await message.answer(f"ОШИБКА i18n ({e})\nНо часы сохранены.", parse_mode=None)
    except Exception as e: # Другие ошибки (БД?)
        try: await message.answer(i18n.generic_db_error(error=str(e)))
        except KeyError: await message.answer(f"Другая ошибка: {e}", parse_mode=None)

    await state.clear()


# --- Удаление пользователя ---
@router.callback_query(F.data == "admin_delete_start")
async def start_delete_user(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    users = await db.get_all_users()
    try:
        if not users:
            await callback.message.edit_text(i18n.admin_no_users_in_db())
            await callback.answer()
            return
        await state.set_state(AdminDeleteUser.waiting_for_user)
        await callback.message.edit_text(
            i18n.admin_select_user_delete(),
            reply_markup=kb.get_user_selection_keyboard(users, prefix="delete_user")
        )
    except (KeyError, TelegramBadRequest) as e:
        await callback.message.edit_text(f"ОШИБКА ({e})\nНе могу показать список.", parse_mode=None)
    await callback.answer()

@router.callback_query(AdminDeleteUser.waiting_for_user, F.data.startswith("delete_user_"))
async def select_user_to_delete(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    user_id_to_delete = int(callback.data.split("_")[-1])
    try:
        if user_id_to_delete == callback.from_user.id:
            await callback.message.edit_text(i18n.admin_delete_self())
            await state.clear()
            await callback.answer()
            return
        user_name = next((name for uid, name in await db.get_all_users() if uid == user_id_to_delete), "???")
        await state.set_state(AdminDeleteUser.waiting_for_confirmation)
        await state.update_data(user_id=user_id_to_delete, user_name=user_name)
        await callback.message.edit_text(
            i18n.admin_delete_confirm(user_name=user_name),
            reply_markup=kb.get_delete_confirmation_keyboard(i18n, user_id_to_delete)
        )
    except (KeyError, TelegramBadRequest) as e:
        await callback.message.edit_text(f"ОШИБКА ({e})\nНе могу показать подтверждение.", parse_mode=None)
        await state.clear()
    await callback.answer()

@router.callback_query(AdminDeleteUser.waiting_for_confirmation, F.data == "delete_confirm_no")
async def cancel_delete_user(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    try:
        await callback.message.edit_text(i18n.admin_delete_cancelled())
    except (KeyError, TelegramBadRequest):
        await callback.message.edit_text("Отменено.", parse_mode=None)
    await state.clear()
    await callback.answer()

@router.callback_query(AdminDeleteUser.waiting_for_confirmation, F.data.startswith("delete_confirm_yes_"))
async def confirm_delete_user(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    user_id_to_delete = int(callback.data.split("_")[-1])
    data = await state.get_data()
    if user_id_to_delete != data.get("user_id"):
        await state.clear()
        await callback.message.edit_text("Ошибка! ID не совпали.", parse_mode=None)
        await callback.answer()
        return
    user_name = data.get("user_name", "???")
    try:
        await db.delete_user(user_id_to_delete)
        await callback.message.edit_text(i18n.admin_delete_success(user_name=user_name)) # HTML для успеха
    except (KeyError, TelegramBadRequest) as e_i18n:
        await callback.message.edit_text(
            f"ОШИБКА ({e_i18n})\nНО: {user_name} (ID: {user_id_to_delete}) УДАЛЕН.", parse_mode=None
        )
    except Exception as e_db:
        await callback.message.edit_text(f"Ошибка БД: {e_db}", parse_mode=None)
    await state.clear()
    await callback.answer()