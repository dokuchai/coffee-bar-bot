# filters.py
from aiogram.filters import Filter
from aiogram.types import Message
from aiogram_i18n import I18nContext

class MagicI18nFilter(Filter):
    """
    Этот фильтр ищет совпадение текста сообщения
    среди ВСЕХ переводов указанного ключа.
    """
    def __init__(self, key: str):
        # 🔽🔽🔽
        # ❗️❗️❗️ ИСПРАВЛЕНИЕ ❗️❗️❗️
        # Мы НЕ преобразуем ключ.
        # i18n.core.get() будет искать "button_help" (с '_')
        # 🔽🔽🔽
        self.key = key

    async def __call__(self, message: Message, i18n: I18nContext) -> bool:
        text = message.text
        if not text:
            return False

        # Убедимся, что Core загружен, прежде чем его использовать
        if not hasattr(i18n, 'core') or not i18n.core:
             print("!!! ОШИБКА ФИЛЬТРА: i18n.core не найден !!!") # Отладка
             return False

        available_locales = i18n.core.locales
        if not available_locales:
             print(f"!!! ОШИБКА ФИЛЬТРА: Нет доступных локалей (ключ: {self.key}) !!!") # Отладка
             return False # Если Core не загрузил языки, не можем ничего проверить

        for locale in available_locales:
            try:
                # 🔽 Ищем ключ как есть (с '_')
                translation = i18n.core.get(self.key, locale)
                # print(f"DEBUG Filter: Text='{text}', Key='{self.key}', Locale='{locale}', Translation='{translation}'") # Отладка
                if text == translation:
                    return True # Нашли!
            except KeyError:
                # Это нормально, если в каком-то языке нет ключа
                continue
            except Exception as e:
                print(f"!!! ОШИБКА ФИЛЬТРА при i18n.core.get('{self.key}', '{locale}'): {e} !!!") # Отладка
                continue

        # print(f"DEBUG Filter: No match found for Text='{text}', Key='{self.key}'") # Отладка
        return False # Совпадений не найдено