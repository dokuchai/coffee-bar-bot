# middlewares/simple_i18n.py
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from typing import Any, Callable, Dict, Awaitable
from .locales_manager import i18n as i18n_obj


class SimpleI18nMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")

        # Берем язык из Telegram (обычно 'ru', 'en', 'sr')
        # Если кода языка нет, ставим 'ru'
        locale = user.language_code if user and user.language_code else "ru"
        print(f"DEBUG: User {user.id} has language_code: {user.language_code}")

        # ВАЖНО: Telegram может вернуть 'en-GB' или 'en-US'
        # Нам нужно взять только первые две буквы
        locale = locale[:2]

        # Проверяем, загружен ли этот язык в наш менеджер
        if locale not in i18n_obj.bundles:
            locale = "ru"  # Если 'en' не загружен, тогда только 'ru'

        def _(key, **kwargs):
            return i18n_obj.get(key, locale=locale, **kwargs)

        data["i18n"] = i18n_obj
        data["_"] = _
        data["locale"] = locale

        return await handler(event, data)