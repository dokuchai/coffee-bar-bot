# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

from config import load_config, BotConfig
from database import init_db
from handlers import common, user_handlers, admin_handlers, group_handlers
from middlewares.simple_i18n import SimpleI18nMiddleware
from middlewares.locales_manager import i18n as i18n_obj

from scheduler.jobs import cron_auto_close_shifts, remind_end_shift
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeDefault


async def set_commands(bot: Bot):
    user_scope = BotCommandScopeAllPrivateChats()

    await bot.delete_my_commands(scope=BotCommandScopeDefault())
    await bot.delete_my_commands(scope=user_scope)

    commands_ru = [
        BotCommand(command="start", description="Главное меню 🏠"),
        BotCommand(command="help", description="Справка и помощь 📖"),
        BotCommand(command="lang", description="Сменить язык 🌍")
    ]

    commands_en = [
        BotCommand(command="start", description="Main menu 🏠"),
        BotCommand(command="help", description="Help & Info 📖"),
        BotCommand(command="lang", description="Change language 🌍")
    ]

    await bot.set_my_commands(commands=commands_ru, scope=user_scope)
    await bot.set_my_commands(commands=commands_ru, scope=user_scope, language_code="ru")
    await bot.set_my_commands(commands=commands_en, scope=user_scope, language_code="en")
    current_commands = await bot.get_my_commands(scope=user_scope)
    logging.info(f"📊 API Telegram подтвердил установку команд: {current_commands}")


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
    dp.update.middleware(SimpleI18nMiddleware())

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
        hour=20,
        minute=0,
        kwargs={"bot": bot, "i18n": i18n_obj}
    )
    # Добавляем задачу: каждый день в 20:30
    scheduler.add_job(
        cron_auto_close_shifts,
        trigger='cron',
        hour=20,
        minute=30,
        kwargs={"bot": bot, "i18n": i18n_obj}
    )

    # --- Start ---
    try:
        await set_commands(bot)
        print("🚀 Команды отправлены в Telegram")
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
