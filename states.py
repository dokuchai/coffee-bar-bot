# states.py
from aiogram.fsm.state import State, StatesGroup

class UserSetup(StatesGroup):
    """Первоначальная настройка ролей."""
    waiting_for_role_selection = State()

class RecordShift(StatesGroup):
    """Состояние записи смены (твой новый метод)."""
    waiting_for_role = State()        # Если >1 роли, выбор роли для НАЧАЛА
    waiting_for_start_time = State()  # Выбор часа НАЧАЛА
    waiting_for_end_time = State()    # Выбор часа ОКОНЧАНИЯ

class AdminManualAdd(StatesGroup):
    """Ручная корректировка."""
    waiting_for_user = State()
    waiting_for_role = State()
    waiting_for_hours = State()

class AdminDeleteUser(StatesGroup):
    """Удаление пользователя."""
    waiting_for_user = State()
    waiting_for_confirmation = State()