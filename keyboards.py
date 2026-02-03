# keyboards.py
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Tuple, Callable
import database as db


# --- Главное меню (Reply) ---
async def get_main_menu_keyboard(i18n: Callable, user_id: int, is_admin: bool = False):
    builder = ReplyKeyboardBuilder()
    status = await db.get_shift_status(user_id)

    # Используем i18n как функцию: i18n("key")
    if status == 'active':
        builder.button(text=i18n("button_end_shift"))
    else:
        builder.button(text=i18n("button_start_shift"))

    builder.button(text=i18n("button_my_stats"))

    if is_admin:
        builder.button(text=i18n("button_admin_panel"))

    builder.adjust(1, 2)
    return builder.as_markup(resize_keyboard=True)


# --- Выбор роли (Inline) ---
def get_role_selection_keyboard(
        i18n: Callable,
        all_roles: List[Tuple[int, str, float]],
        selected_role_ids: List[int] = [],
        is_setup: bool = False,
        prefix: str = "select_role_"
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for role_id, role_name, _ in all_roles:
        text = role_name
        callback_data = f"{prefix}{role_id}"
        if is_setup:
            if role_id in selected_role_ids:
                text = f"✅ {role_name}"
            callback_data = f"setup_toggle_role_{role_id}"
        builder.row(InlineKeyboardButton(text=text, callback_data=callback_data))

    if is_setup:
        builder.row(InlineKeyboardButton(text=i18n("button_done"), callback_data="setup_finish_roles"))

    return builder.as_markup()


# --- Админ-панель ---
def get_admin_panel_keyboard(i18n: Callable) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=i18n("admin_button_report_day"), callback_data="admin_rep:today"),
        InlineKeyboardButton(text=i18n("admin_button_report_week"), callback_data="admin_rep:week")
    )
    builder.row(
        InlineKeyboardButton(text=i18n("admin_button_report_month"), callback_data="admin_rep:month"),
        InlineKeyboardButton(text=i18n("admin_button_report_prev_month"), callback_data="admin_rep:prev_month")
    )
    builder.row(InlineKeyboardButton(text=i18n("admin_button_manual_add"), callback_data="admin_manual_add"))
    builder.row(InlineKeyboardButton(text=i18n("admin_button_delete_user"), callback_data="admin_delete_start"))
    return builder.as_markup()


# --- ВЫБОР ЮЗЕРА ДЛЯ ОТЧЕТОВ ---
def get_users_report_keyboard(i18n: Callable, period: str, users: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Заменили хардкод на ключи из .ftl
    builder.row(InlineKeyboardButton(text=i18n("admin_button_total_view"), callback_data=f"total_view:{period}"))
    for user_id, first_name in users:
        builder.row(InlineKeyboardButton(text=first_name, callback_data=f"view_rep:{period}:{user_id}"))

    builder.row(InlineKeyboardButton(text=i18n("admin_button_back"), callback_data="admin_panel"))
    return builder.as_markup()


# --- ВЫБОР ЮЗЕРА ДЛЯ КОРРЕКТИРОВКИ / УДАЛЕНИЯ ---
def get_user_selection_keyboard(i18n: Callable, users: list[tuple[int, str]], prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user_id, first_name in users:
        builder.row(InlineKeyboardButton(text=first_name, callback_data=f"{prefix}_{user_id}"))

    builder.row(InlineKeyboardButton(text=i18n("admin_button_back"), callback_data="admin_panel"))
    return builder.as_markup()


# --- Подтверждение удаления ---
def get_delete_confirmation_keyboard(i18n: Callable, user_id_to_delete: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=i18n("admin_delete_confirm_yes"),
                             callback_data=f"delete_confirm_yes_{user_id_to_delete}"),
        InlineKeyboardButton(text=i18n("admin_delete_confirm_no"), callback_data="admin_panel")
    )
    return builder.as_markup()


# --- Статистика пользователя ---
def get_user_stats_keyboard(i18n: Callable):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=i18n("stats_button_week"), callback_data="usr_st:week"),
        InlineKeyboardButton(text=i18n("stats_button_month"), callback_data="usr_st:month")
    )
    return builder.as_markup()


def get_language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
        InlineKeyboardButton(text="🇺🇸 English", callback_data="set_lang:en")
    )
    return builder.as_markup()
