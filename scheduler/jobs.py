# scheduler/jobs.py
import logging
from datetime import date, datetime

import aiosqlite
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound
# ---
#❗️❗️❗️ CHANGE: Import Core and Manager types ❗️❗️❗️
# ---
from aiogram_i18n.cores import BaseCore
from aiogram_i18n.managers import BaseManager
import database as db


# ---
#❗️❗️❗️ CHANGE: Function signature now accepts core and manager ❗️❗️❗️
# ---
async def remind_end_shift(bot: Bot, i18n_core: BaseCore, i18n_manager: BaseManager):
    """
    Finds users with recorded shift starts and reminds them to end it.
    """
    logging.info(f"Scheduler: Checking started shifts for reminders.")

    # 1. Get users with recorded starts
    active_shifts_info = await db.get_users_with_recorded_start()  # Gets [(uid, rid, sdate_str), ...]

    if not active_shifts_info:
        logging.info("Scheduler: No started shifts found.")
        return

    today_str = date.today().isoformat()
    users_to_remind = [info[0] for info in active_shifts_info if info[2] == today_str]

    if not users_to_remind:
        logging.info("Scheduler: No shifts started TODAY found.")
        return

    logging.info(f"Scheduler: Found {len(users_to_remind)} shifts started today to remind.")

    # 2. Get reminder text using core and manager directly
    try:
        # ---
        #❗️❗️❗️ CHANGE: Use core.get() and manager.default_locale ❗️❗️❗️
        # ---
        reminder_text = i18n_core.get(
            "reminder_end_shift",  # Key with underscore
            i18n_manager.default_locale
        )
    except KeyError:
        reminder_text = "⏰ Напоминание! Пожалуйста, не забудьте завершить текущую смену, нажав 'Записать смену' и выбрав время окончания."
        logging.error("Scheduler: Key 'reminder_end_shift' not found in .ftl! Using default text.")
    except Exception as e:
        reminder_text = "⏰ Напоминание! Пожалуйста, не забудьте завершить текущую смену, нажав 'Записать смену' и выбрав время окончания."
        logging.error(f"Scheduler: Error getting text from i18n Core: {e}")

    # 3. Send reminders
    sent_count = 0
    failed_count = 0
    for user_id in users_to_remind:
        try:
            await bot.send_message(user_id, reminder_text)
            sent_count += 1
            logging.debug(f"Scheduler: Reminder 'End shift' sent to user {user_id}")
        except (TelegramForbiddenError, TelegramNotFound):
            logging.warning(f"Scheduler: Failed to send reminder to {user_id} (blocked/not found).")
            failed_count += 1
        except Exception as e:
            logging.error(f"Scheduler: Unknown error sending to {user_id}: {e}")
            failed_count += 1

    logging.info(f"Scheduler: Reminders 'End shift' sent to {sent_count} users, failed for {failed_count}.")


async def cron_auto_close_shifts(bot):
    # Нам нужен список ID тех, у кого смены открыты
    import aiosqlite
    async with aiosqlite.connect(db.DB_NAME) as conn:
        async with conn.execute("SELECT DISTINCT user_id FROM shifts WHERE end_time IS NULL") as c:
            users = await c.fetchall()

    closing_time = datetime.now().replace(hour=20, minute=30, second=0, microsecond=0)

    for (uid,) in users:
        mins = await db.close_shift(uid, end_dt=closing_time)
        if mins is not None:
            h, m = divmod(mins, 60)
            await bot.send_message(uid, f"⏰ Ваша смена была автоматически закрыта в 20:30.\nИтог: {h} ч. {m} м.")
