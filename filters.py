# filters.py
import logging
from aiogram.filters import Filter
from aiogram.types import Message
from typing import Callable


class MagicI18nFilter(Filter):
    def __init__(self, key: str):
        self.key = key

    async def __call__(self, message: Message, _: Callable) -> bool:
        if not message.text:
            return False

        translated_text = _(self.key)

        # Печатаем в консоль для проверки
        logging.info(f"DEBUG FILTER: На кнопке='{message.text}', Ждали='{translated_text}' (ключ: {self.key})")

        return message.text == translated_text