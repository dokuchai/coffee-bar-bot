# keyboards.py
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram_i18n import I18nContext
from typing import List, Tuple
import database as db


async def get_main_menu_keyboard(i18n, user_id, is_admin=False):
    builder = ReplyKeyboardBuilder()
    status = await db.get_shift_status(user_id)

    if status == 'active':
        builder.button(text=i18n.button_end_shift())
    elif status == 'none':
        # Появится снова, если отработал одну роль, но осталась вторая
        builder.button(text=i18n.button_start_shift())
    else:
        # 'finished_all' - кнопок управления сменой нет
        pass

    builder.button(text=i18n.button_my_stats())
    builder.button(text=i18n.button_help())

    if is_admin:
        builder.button(text=i18n.button_admin_panel())

    builder.adjust(1, 2)
    return builder.as_markup(resize_keyboard=True)


def get_user_stats_keyboard(i18n):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=i18n.stats_button_week(), callback_data="usr_st:week"),
        InlineKeyboardButton(text=i18n.stats_button_month(), callback_data="usr_st:month")
    )
    return builder.as_markup()


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
    builder.row(
        InlineKeyboardButton(
            text=i18n.admin_button_report_prev_month(),
            callback_data="admin_report_prev_month"
        )
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
