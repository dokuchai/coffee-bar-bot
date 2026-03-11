# states.py
from aiogram.fsm.state import State, StatesGroup

class UserSetup(StatesGroup):
    """Первоначальная настройка ролей."""
    waiting_for_role_selection = State()

class AdminManualAdd(StatesGroup):
    """Ручная корректировка."""
    waiting_for_user = State()
    waiting_for_role = State()
    waiting_for_hours = State()

class AdminDeleteUser(StatesGroup):
    """Удаление пользователя."""
    waiting_for_user = State()
    waiting_for_confirmation = State()