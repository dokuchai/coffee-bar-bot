# middlewares/i18n.py
from typing import Any, Dict, Optional, Tuple
from aiogram.types import TelegramObject, User
from pathlib import Path
import os
from aiogram_i18n import I18nMiddleware
from aiogram_i18n.cores import FluentRuntimeCore, BaseCore
from aiogram_i18n.managers import BaseManager

class CustomManager(BaseManager):
    def __init__(self, default_locale: str):
        super().__init__(default_locale=default_locale)

    async def get_locale(self, event: TelegramObject) -> str:
        user: User or None = None
        if hasattr(event, "from_user"):
            user = event.from_user
        if user and user.language_code:
            language_code = user.language_code
            # Use self.core from BaseManager after middleware is set up
            if hasattr(self, 'core') and self.core:
                 available_locales = self.core.locales
                 if language_code in available_locales:
                     return language_code
                 for locale in available_locales:
                     if language_code.startswith(locale):
                         return locale
        return self.default_locale

    async def set_locale(self, locale: str, data: Dict[str, Any]) -> None:
        pass

# ---
#❗️❗️❗️ CHANGE: Function now returns Core and Manager too ❗️❗️❗️
# ---
def setup_i18n(dp, default_locale: str) -> Tuple[I18nMiddleware, BaseCore, BaseManager]:
    """
    Sets up, registers, and RETURNS i18n middleware, core, and manager.
    """
    project_root = Path(__file__).parent.parent
    locales_path = str(project_root / "locales")

    # 1. Create Core
    core = FluentRuntimeCore(path=locales_path)
    print(f"DEBUG: Path used for i18n Core: {locales_path}")
    print(f"DEBUG: Locales loaded by Core: {core.locales}") # Check loaded locales

    # 2. Create Manager
    manager = CustomManager(default_locale=default_locale)

    # 3. Create Middleware
    i18n = I18nMiddleware(core=core, manager=manager)

    # 4. Register Middleware
    i18n.setup(dp)

    # 5. Return all components needed elsewhere
    return i18n, core, manager