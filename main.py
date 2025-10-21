# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
# ---
#❗️❗️❗️ CHANGE: Import Core and Manager types ❗️❗️❗️
# ---
from aiogram_i18n.cores import BaseCore
from aiogram_i18n.managers import BaseManager

from config import load_config, BotConfig
from database import init_db
from handlers import common, user_handlers, admin_handlers, group_handlers
from middlewares.i18n import setup_i18n
# ---
#❗️❗️❗️ CHANGE: Import correct job function name if needed (should be remind_end_shift) ❗️❗️❗️
# ---
from scheduler.jobs import remind_end_shift

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    config = load_config()
    await init_db()
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # --- Setup I18N ---
    DEFAULT_LOCALE = "ru"
    # ---
    #❗️❗️❗️ CHANGE: Get core and manager back from setup_i18n ❗️❗️❗️
    # ---
    i18n_middleware, i18n_core, i18n_manager = setup_i18n(dp, DEFAULT_LOCALE)

    # --- Pass config ---
    dp["config"] = config.bot

    # --- Register Routers ---
    dp.include_router(group_handlers.router)
    dp.include_router(common.router)
    dp.include_router(user_handlers.router)
    admin_router = Router()
    admin_router.include_router(admin_handlers.router)
    admin_router.message.filter(F.from_user.id.in_(config.bot.admin_ids))
    admin_router.callback_query.filter(F.from_user.id.in_(config.bot.admin_ids))
    dp.include_router(admin_router)

    # --- Scheduler ---
    timezone = pytz.timezone('Europe/Belgrade')
    scheduler = AsyncIOScheduler(timezone=timezone)
    scheduler.add_job(
        remind_end_shift,
        trigger='cron',
        hour="*",
        minute="*",
        # ---
        #❗️❗️❗️ CHANGE: Pass core and manager instead of middleware ❗️❗️❗️
        # ---
        args=[bot, i18n_core, i18n_manager]
    )

    # --- Start ---
    try:
        scheduler.start()
        logging.info("Scheduler started.")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")