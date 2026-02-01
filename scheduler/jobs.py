# scheduler/jobs.py
import logging
from datetime import datetime, time
import aiosqlite
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound
from aiogram_i18n.cores import BaseCore
from aiogram_i18n.managers import BaseManager

import database as db


# --- 1. Напоминание о завершении смены ---
async def remind_end_shift(bot: Bot, i18n_core: BaseCore, i18n_manager: BaseManager):
    logging.info("Scheduler: Checking started shifts for reminders.")

    # Получаем список тех, у кого смена не закрыта
    # Предполагаем, что функция возвращает [(user_id, role_id, start_time_str), ...]
    active_shifts = await db.get_users_with_active_shifts()

    if not active_shifts:
        logging.info("Scheduler: No active shifts found.")
        return

    today_str = db.get_today().isoformat()

    # Отбираем только тех, кто начал смену СЕГОДНЯ (чтобы не спамить старыми хвостами)
    # Предполагаем, что start_time_str — это ISO строка "YYYY-MM-DDTHH:MM:SS"
    users_to_remind = [s[0] for s in active_shifts if s[2].startswith(today_str)]

    if not users_to_remind:
        logging.info("Scheduler: No shifts started TODAY found.")
        return

    # Получаем текст напоминания (всегда используем локаль по умолчанию,
    # так как в джобе нет контекста конкретного пользователя)
    try:
        reminder_text = i18n_core.get("reminder_end_shift", i18n_manager.default_locale)
    except Exception:
        reminder_text = "⏰ Напоминание! Пожалуйста, не забудьте завершить текущую смену."

    sent_count = 0
    for user_id in users_to_remind:
        try:
            await bot.send_message(user_id, reminder_text)
            sent_count += 1
        except (TelegramForbiddenError, TelegramNotFound):
            logging.warning(f"Scheduler: User {user_id} blocked the bot.")
        except Exception as e:
            logging.error(f"Scheduler: Error sending to {user_id}: {e}")

    logging.info(f"Scheduler: Reminders sent to {sent_count} users.")


# --- 2. Автоматическое закрытие смен ---
async def cron_auto_close_shifts(bot: Bot, i18n_core: BaseCore, i18n_manager: BaseManager):
    logging.info("Scheduler: Running auto-close for all active shifts.")

    # 1. Находим всех, у кого не закрыта смена
    async with aiosqlite.connect(db.DB_NAME) as conn:
        async with conn.execute("SELECT DISTINCT user_id FROM shifts WHERE end_time IS NULL") as c:
            users = await c.fetchall()

    if not users:
        logging.info("Scheduler: No shifts to auto-close.")
        return

    # Устанавливаем время закрытия: сегодня, 20:30 (Белград)
    # Используем replace(tzinfo=None), чтобы не было конфликта aware/naive при вычитании в БД
    now_serbia = db.get_now()
    closing_time = now_serbia.replace(hour=20, minute=30, second=0, microsecond=0, tzinfo=None)

    for (uid,) in users:
        # Мы вызываем функцию закрытия, передавая ей жесткое время 20:30
        # Обязательно убедись, что db.record_shift_end принимает аргумент end_dt
        mins = await db.close_shift(uid, end_dt=closing_time)

        if mins is not None:
            time_str = db.format_minutes_to_str(mins)

            # Локализация сообщения об автозакрытии
            try:
                msg = i18n_core.get("auto_close_notification", i18n_manager.default_locale, time_str=time_str)
            except:
                msg = f"⏰ Ваша смена была автоматически закрыта в 20:30.\nИтог: {time_str}"

            try:
                await bot.send_message(uid, msg)
            except Exception as e:
                logging.error(f"Scheduler: Could not notify user {uid} about auto-close: {e}")

    logging.info(f"Scheduler: Auto-closed shifts for {len(users)} users.")