# middlewares/locales_manager.py
import os
from pathlib import Path
from fluent.runtime import FluentResource, FluentBundle


class LocaleManager:
    def __init__(self, default_locale="ru"):
        self.default_locale = default_locale
        self.bundles = {}
        self.load_locales()

    def load_locales(self):
        locales_dir = Path(__file__).parent.parent / "locales"
        for locale in ["ru", "en", "sr"]:  # Список твоих языков
            path = locales_dir / locale / "messages.ftl"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    resource = FluentResource(f.read())
                    bundle = FluentBundle([locale])
                    bundle.add_resource(resource)
                    self.bundles[locale] = bundle
                print(f"✅ Локаль {locale} загружена вручную.")

    def get(self, key, locale="ru", **kwargs):
        bundle = self.bundles.get(locale, self.bundles.get(self.default_locale))
        if not bundle:
            return key

        message = bundle.get_message(key)
        if not message or not message.value:
            return key

        try:
            # Вызываем форматирование
            result = bundle.format_pattern(message.value, kwargs)

            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ:
            # Если результат — это кортеж (текст, ошибки), берем только текст [0]
            if isinstance(result, tuple):
                return result[0]

            return result
        except Exception as e:
            print(f"⚠️ Ошибка форматирования ключа '{key}': {e}")
            return key


# Создаем глобальный объект
i18n = LocaleManager()