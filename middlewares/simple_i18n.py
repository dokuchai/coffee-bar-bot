# middlewares/simple_i18n.py
from aiogram import BaseMiddleware
from .locales_manager import i18n as i18n_obj
import database as db
import logging


class SimpleI18nMiddleware:
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        user_id = user.id

        try:
            # Пытаемся достать язык из базы
            locale = await db.get_user_locale(user_id)
        except Exception as e:
            logging.error(f"❌ Ошибка БД в Middleware: {e}")
            locale = None

        # Если в базе пусто или ошибка — берем из Telegram
        if not locale:
            locale = user.language_code[:2] if user.language_code else "ru"

        # Проверка на поддержку языка менеджером
        if locale not in i18n_obj.bundles:
            locale = "ru"

        def _(key, **kwargs):
            return i18n_obj.get(key, locale=locale, **kwargs)

        data["_"] = _
        data["locale"] = locale
        data["i18n"] = i18n_obj

        return await handler(event, data)
