# keyboards.py
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_i18n import I18nContext
from typing import List, Tuple

def get_main_menu_keyboard(i18n: I18nContext, is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Главная Reply-клавиатура. Всегда показывает "Записать смену".
    """
    kb = [
        [KeyboardButton(text=i18n.button_record_shift())], # Всегда эта кнопка
        [KeyboardButton(text=i18n.button_my_stats()), KeyboardButton(text=i18n.button_help())]
    ]
    if is_admin:
        kb.append([KeyboardButton(text=i18n.button_admin_panel())])

    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder=i18n.input_placeholder()
    )

# --- Клавиатура выбора ролей ---
def get_role_selection_keyboard(
    i18n: I18nContext,
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
        builder.row(InlineKeyboardButton(text=i18n.button_done(), callback_data="setup_finish_roles"))
    return builder.as_markup()

# --- Клавиатуры выбора времени ---
def get_time_selection_keyboard(start: int, end: int, prefix: str) -> InlineKeyboardMarkup:
    """Создает инлайн-клавиатуру для выбора времени."""
    builder = InlineKeyboardBuilder()
    for hour in range(start, end + 1):
        builder.add(InlineKeyboardButton(
            text=f"{hour}:00",
            callback_data=f"{prefix}_{hour}" # Префикс 'start_' или 'end_'
        ))
    builder.adjust(4)
    return builder.as_markup()

def get_start_time_keyboard() -> InlineKeyboardMarkup:
    # Кнопки с 9:00 до 20:00
    return get_time_selection_keyboard(9, 20, "start")

def get_end_time_keyboard() -> InlineKeyboardMarkup:
    # Кнопки с 10:00 до 20:00
    return get_time_selection_keyboard(10, 20, "end")

# --- Клавиатуры статистики, админки, выбора юзера, удаления ---
def get_stats_period_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=i18n.stats_button_week(), callback_data="stats_week"),
        InlineKeyboardButton(text=i18n.stats_button_month(), callback_data="stats_month")
    )
    return builder.as_markup()

def get_admin_panel_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=i18n.admin_button_report_day(), callback_data="admin_report_day"),
        InlineKeyboardButton(text=i18n.admin_button_report_week(), callback_data="admin_report_week"),
        InlineKeyboardButton(text=i18n.admin_button_report_month(), callback_data="admin_report_month")
    )
    builder.row(InlineKeyboardButton(text=i18n.admin_button_manual_add(), callback_data="admin_manual_add"))
    builder.row(InlineKeyboardButton(text=i18n.admin_button_delete_user(), callback_data="admin_delete_start"))
    return builder.as_markup()

def get_user_selection_keyboard(users: list[tuple[int, str]], prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user_id, first_name in users:
        builder.row(InlineKeyboardButton(
            text=first_name,
            callback_data=f"{prefix}_{user_id}"
        ))
    return builder.as_markup()

def get_delete_confirmation_keyboard(i18n: I18nContext, user_id_to_delete: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=i18n.admin_delete_confirm_yes(),
            callback_data=f"delete_confirm_yes_{user_id_to_delete}"
        ),
        InlineKeyboardButton(
            text=i18n.admin_delete_confirm_no(),
            callback_data="delete_confirm_no"
        )
    )
    return builder.as_markup()