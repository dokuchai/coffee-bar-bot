# handlers/admin_handlers.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from datetime import date, timedelta
from aiogram_i18n import I18nContext
from decimal import Decimal

from filters import MagicI18nFilter
import database as db
import keyboards as kb
from states import AdminManualAdd, AdminDeleteUser
from config import BotConfig
from database import get_today

router = Router()


# --- Вспомогательная функция для расчета дат ---
def get_dates_by_period(period: str):
    today = get_today()
    if period == "today":
        return today, today, "сегодня"
    elif period == "week":
        s_date = today - timedelta(days=today.weekday())
        return s_date, today, "эту неделю"
    elif period == "month":
        s_date = today.replace(day=1)
        return s_date, today, "этот месяц"
    elif period == "prev_month":
        first_day_this_month = today.replace(day=1)
        e_date = first_day_this_month - timedelta(days=1)
        s_date = e_date.replace(day=1)
        return s_date, e_date, "прошлый месяц"
    return today, today, "период"


# --- Главное меню админа ---
@router.message(MagicI18nFilter("button_admin_panel"))
async def admin_panel(message: Message, i18n: I18nContext, config: BotConfig):
    user_id = message.from_user.id
    await db.add_or_update_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    await message.answer(
        i18n.admin_panel_welcome(),
        reply_markup=kb.get_admin_panel_keyboard(i18n)
    )


# --- 1. ВЫБОР: ОБЩИЙ ИТОГ ИЛИ СОТРУДНИК ---
@router.callback_query(F.data.startswith("admin_rep:"))
async def admin_report_select_type(callback: CallbackQuery, i18n: I18nContext):
    period = callback.data.split(":")[1]
    _, _, p_text = get_dates_by_period(period)

    users = await db.get_all_users()
    if not users:
        await callback.answer("Сотрудники не найдены", show_alert=True)
        return

    # Вызываем новую клавиатуру с кнопкой "ОБЩИЙ ИТОГ" вверху
    await callback.message.edit_text(
        f"📋 Отчеты за <b>{p_text}</b>.\nВыберите сотрудника или посмотрите общий итог:",
        reply_markup=kb.get_users_report_keyboard(period, users)
    )
    await callback.answer()


# --- 2. ОБЩИЙ ИТОГ ПО ВСЕМ ---
@router.callback_query(F.data.startswith("total_view:"))
async def admin_total_report_by_period(callback: CallbackQuery, i18n: I18nContext):
    period = callback.data.split(":")[1]
    s_date, e_date, p_name = get_dates_by_period(period)

    user_totals, g_mins, g_money = await db.get_total_summary_report(s_date, e_date)

    if not user_totals:
        await callback.answer(f"За {p_name} данных нет", show_alert=True)
        return

    report = [
        f"🧾 <b>ОБЩИЙ ОТЧЕТ: {p_name.upper()}</b>",
        f"📅 {s_date} — {e_date}",
        "---"
    ]

    for name, data in user_totals.items():
        h_str = db.format_minutes_to_str(data["mins"])
        report.append(f"👤 {name}: <b>{h_str}</b> | {data['money']} RSD")

    report.append("---")
    report.append(f"💰 <b>ИТОГО К ВЫПЛАТЕ: {g_money} RSD</b>")

    # Кнопка возврата к выбору сотрудников того же периода
    back_kb = InlineKeyboardBuilder()
    back_kb.button(text="⬅️ Назад к списку", callback_data=f"admin_rep:{period}")

    await callback.message.edit_text("\n".join(report), reply_markup=back_kb.as_markup())
    await callback.answer()


# --- 3. ДЕТАЛЬНЫЙ ОТЧЕТ ПО СОТРУДНИКУ ---
@router.callback_query(F.data.startswith("view_rep:"))
async def admin_report_detailed(callback: CallbackQuery, i18n: I18nContext):
    _, period, uid = callback.data.split(":")
    uid = int(uid)
    s_date, e_date, _ = get_dates_by_period(period)

    minutes, total_money, shifts = await db.get_user_shifts_report(uid, s_date, e_date)

    all_users = await db.get_all_users()
    user_name = next((n for i, n in all_users if i == uid), "Сотрудник")

    if not shifts:
        await callback.message.edit_text(
            f"❌ У <b>{user_name}</b> нет смен за период {s_date} — {e_date}.",
            reply_markup=kb.get_admin_panel_keyboard(i18n)
        )
        return

    h_str = db.format_minutes_to_str(minutes)

    report_lines = [
        f"👤 <b>{user_name}</b>",
        f"📅 Период: {s_date} — {e_date}",
        f"⏱ Итого времени: <b>{h_str}</b>",
        "---"
    ]
    report_lines.extend(shifts)
    report_lines.append("---")
    report_lines.append(f"💰 <b>ИТОГО К ВЫПЛАТЕ: {total_money} RSD</b>")

    if any("🟢" in s or "⚡️" in s for s in shifts):
        report_lines.append("\n🟢 <i>Смена ещё идет, расчет актуален на текущий момент.</i>")

    # Кнопка возврата к списку этого же периода
    back_kb = InlineKeyboardBuilder()
    back_kb.button(text="⬅️ К списку сотрудников", callback_data=f"admin_rep:{period}")

    text = "\n".join(report_lines)
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            await callback.message.answer(text[x:x + 4000])
    else:
        await callback.message.edit_text(text, reply_markup=back_kb.as_markup())
    await callback.answer()


# --- Кнопка "Назад" в админ-панель (общая) ---
@router.callback_query(F.data == "admin_panel")
async def back_to_admin_main(callback: CallbackQuery, i18n: I18nContext):
    await callback.message.edit_text(
        i18n.admin_panel_welcome(),
        reply_markup=kb.get_admin_panel_keyboard(i18n)
    )
    await callback.answer()


# --- РУЧНАЯ КОРРЕКТИРОВКА ---
@router.callback_query(F.data == "admin_manual_add")
async def start_manual_add(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    users = await db.get_all_users()
    if not users:
        await callback.message.edit_text("В базе нет пользователей.")
        return
    await state.set_state(AdminManualAdd.waiting_for_user)
    await callback.message.edit_text(
        i18n.admin_select_user_adjust(),
        reply_markup=kb.get_user_selection_keyboard(users, prefix="manual_user")
    )


@router.callback_query(AdminManualAdd.waiting_for_user, F.data.startswith("manual_user_"))
async def manual_add_user_selected(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    uid = int(callback.data.split("_")[-1])
    all_u = await db.get_all_users()
    uname = next((n for i, n in all_u if i == uid), "???")
    await state.update_data(user_id=uid, user_name=uname)

    uroles = await db.get_user_roles(uid)
    if not uroles:
        await callback.message.edit_text("У этого пользователя нет ролей.")
        await state.clear()
        return

    if len(uroles) == 1:
        rid, rn, _ = uroles[0]
        await state.update_data(role_id=rid, role_name=rn)
        await state.set_state(AdminManualAdd.waiting_for_hours)
        await callback.message.edit_text(i18n.adjust_user_selected_single_role(user_name=uname, role_name=rn))
    else:
        await state.set_state(AdminManualAdd.waiting_for_role)
        await callback.message.edit_text(
            i18n.adjust_select_role(user_name=uname),
            reply_markup=kb.get_role_selection_keyboard(i18n, uroles, prefix="adjust_role_")
        )


@router.callback_query(AdminManualAdd.waiting_for_role, F.data.startswith("adjust_role_"))
async def manual_add_role_selected(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    rid = int(callback.data.split("_")[-1])
    all_r = await db.get_roles()
    rn = next((n for i, n, _ in all_r if i == rid), "???")
    await state.update_data(role_id=rid, role_name=rn)
    await state.set_state(AdminManualAdd.waiting_for_hours)
    data = await state.get_data()
    await callback.message.edit_text(i18n.adjust_user_selected_multi_role(user_name=data['user_name'], role_name=rn))


@router.message(AdminManualAdd.waiting_for_hours)
async def manual_add_minutes_entered(message: Message, state: FSMContext, i18n: I18nContext):
    try:
        minutes_to_add = int(message.text.strip())
        if minutes_to_add == 0: raise ValueError
    except ValueError:
        await message.answer(i18n.adjust_error_format())
        return

    data = await state.get_data()
    uid, rid, uname, rname = data['user_id'], data['role_id'], data['user_name'], data['role_name']
    today = get_today()

    # Сохранение корректировки (в минутах)
    try:
        await db.add_manual_adjustment(uid, rid, minutes_to_add)
        await message.answer(
            i18n.adjust_success_with_role(
                user_name=uname, role_name=rname,
                date=today.isoformat(), hours_str=f"{minutes_to_add:+}"
            )
        )
    except Exception as e:
        await message.answer(f"Ошибка БД: {e}")

    await state.clear()


# --- УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ ---
@router.callback_query(F.data == "admin_delete_start")
async def start_delete_user(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    users = await db.get_all_users()
    if not users:
        await callback.message.edit_text("В базе нет пользователей.")
        return
    await state.set_state(AdminDeleteUser.waiting_for_user)
    await callback.message.edit_text(
        i18n.admin_select_user_delete(),
        reply_markup=kb.get_user_selection_keyboard(users, prefix="delete_user")
    )


@router.callback_query(AdminDeleteUser.waiting_for_user, F.data.startswith("delete_user_"))
async def select_user_to_delete(callback: CallbackQuery, state: FSMContext, i18n: I18nContext):
    user_id_to_delete = int(callback.data.split("_")[-1])
    if user_id_to_delete == callback.from_user.id:
        await callback.message.edit_text("Нельзя удалить самого себя!")
        await state.clear()
        return

    all_u = await db.get_all_users()
    user_name = next((name for uid, name in all_u if uid == user_id_to_delete), "???")
    await state.update_data(user_id=user_id_to_delete, user_name=user_name)
    await state.set_state(AdminDeleteUser.waiting_for_confirmation)
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить сотрудника <b>{user_name}</b>?\nВся история смен будет стерта!",
        reply_markup=kb.get_delete_confirmation_keyboard(i18n, user_id_to_delete)
    )


@router.callback_query(AdminDeleteUser.waiting_for_confirmation, F.data == "delete_confirm_no")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Удаление отменено.")
    await state.clear()


@router.callback_query(AdminDeleteUser.waiting_for_confirmation, F.data.startswith("delete_confirm_yes_"))
async def confirm_delete(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    await db.delete_user(user_id)
    await callback.message.edit_text("✅ Пользователь успешно удален.")
    await state.clear()