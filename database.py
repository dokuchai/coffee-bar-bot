# database.py
import aiosqlite
from datetime import date, datetime, timedelta, time
from typing import Optional, List, Tuple, Dict

DB_NAME = 'coffee_bot.db'

# Роли и ставки
ROLES_DATA = [
    (1, 'Помощник повара', 371.0),
    (2, 'Повар', 380.5),
    (3, 'Бариста', 371.0)
]

async def init_db():
    """Инициализирует/обновляет БД."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Включаем поддержку внешних ключей
        await db.execute("PRAGMA foreign_keys = ON")

        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT
            )
        ''')
        # Таблица ролей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                role_id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                rate REAL NOT NULL
            )
        ''')
        # Таблица связи Пользователь <-> Роль
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, role_id)
            )
        ''')
        # Таблица завершенных смен
        await db.execute('''
            CREATE TABLE IF NOT EXISTS shifts (
                shift_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role_id INTEGER,
                shift_date TEXT NOT NULL,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,
                hours_worked REAL NOT NULL,
                rate_at_time REAL,
                entry_type TEXT NOT NULL DEFAULT 'auto',
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE SET NULL
            )
        ''')

        async with db.execute("PRAGMA table_info(shifts)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
            if 'rate_at_time' not in columns:
                await db.execute("ALTER TABLE shifts ADD COLUMN rate_at_time REAL")
                # Заполняем ставку для старых записей из текущей таблицы ролей
                await db.execute('''
                    UPDATE shifts 
                    SET rate_at_time = (
                        SELECT rate FROM roles WHERE roles.role_id = shifts.role_id
                    )
                    WHERE rate_at_time IS NULL
                ''')

        # Таблица для записи НАЧАЛА смен (по твоему методу)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS active_shifts (
                user_id INTEGER PRIMARY KEY,
                role_id INTEGER NOT NULL,
                start_hour INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE CASCADE
            )
        ''')
        # Обновляем или вставляем роли и их ставки (ON CONFLICT для обновления текущих ставок)
        for role_id, name, rate in ROLES_DATA:
            await db.execute('''
                    INSERT INTO roles (role_id, name, rate) VALUES (?, ?, ?)
                    ON CONFLICT(role_id) DO UPDATE SET rate = excluded.rate, name = excluded.name
                    ''', (role_id, name, rate))
        await db.commit()

# --- Функции users, roles, user_roles ---
async def add_or_update_user(user_id: int, username: str, first_name: str):
     async with aiosqlite.connect(DB_NAME) as db:
         await db.execute(
             "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?) "
             "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name",
             (user_id, username or '', first_name or '') # Защита от None
         )
         await db.commit()

async def get_roles() -> List[Tuple[int, str, float]]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT role_id, name, rate FROM roles ORDER BY role_id") as cursor:
            return await cursor.fetchall()

async def check_user_has_roles(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT 1 FROM user_roles WHERE user_id = ? LIMIT 1", (user_id,)) as cursor:
            return await cursor.fetchone() is not None

async def get_user_roles(user_id: int) -> List[Tuple[int, str, float]]:
    query = """
        SELECT r.role_id, r.name, r.rate
        FROM user_roles ur
        JOIN roles r ON ur.role_id = r.role_id
        WHERE ur.user_id = ?
        ORDER BY r.role_id
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, (user_id,)) as cursor:
            return await cursor.fetchall()

async def set_user_roles(user_id: int, role_ids: List[int]):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
        if role_ids:
            await db.executemany(
                "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                [(user_id, rid) for rid in role_ids]
            )
        await db.commit()

# --- Функции для active_shifts (с часами) ---
async def record_shift_start(user_id: int, role_id: int, start_hour: int):
    """Записывает начало смены в active_shifts."""
    today_str = date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        # INSERT OR REPLACE на случай, если старая запись осталась
        await db.execute(
            "INSERT OR REPLACE INTO active_shifts (user_id, role_id, start_hour, start_date) VALUES (?, ?, ?, ?)",
            (user_id, role_id, start_hour, today_str)
        )
        await db.commit()

async def get_recorded_shift_start(user_id: int) -> Optional[Tuple[int, int, date]]:
    """Возвращает (role_id, start_hour, start_date) начатой смены, если есть."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT role_id, start_hour, start_date FROM active_shifts WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                role_id, start_hour, start_date_str = row
                start_date_obj = date.fromisoformat(start_date_str)
                return role_id, start_hour, start_date_obj
            return None

async def delete_recorded_shift_start(user_id: int):
    """Удаляет запись о начатой смене из active_shifts."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM active_shifts WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_users_with_recorded_start() -> List[Tuple[int, int, str]]:
    """Возвращает (user_id, role_id, start_date) для напоминания."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, role_id, start_date FROM active_shifts") as cursor:
            return await cursor.fetchall()

# --- Функция get_user_shifts_for_day (для валидации) ---
async def get_user_shifts_for_day(user_id: int, shift_date: date) -> list[tuple[int, int]]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT start_time, end_time FROM shifts "
            "WHERE user_id = ? AND shift_date = ? AND entry_type = 'auto'",
            (user_id, shift_date.isoformat())
        ) as cursor:
            return await cursor.fetchall()

# --- Вспомогательная функция для получения текущей ставки роли ---
async def _get_current_role_rate(role_id: int) -> float:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT rate FROM roles WHERE role_id = ?", (role_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0.0

# --- Функция add_shift (для ЗАВЕРШЕННЫХ смен) ---
async def add_shift(user_id: int, role_id: int, start_hour: int, end_hour: int):
    today = date.today().isoformat()
    hours_worked = float(end_hour - start_hour)
    current_rate = await _get_current_role_rate(role_id)  # Берем ставку на момент записи
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            """INSERT INTO shifts
               (user_id, role_id, shift_date, start_time, end_time, hours_worked, rate_at_time, entry_type)
               VALUES (?, ?, ?, ?, ?, ?, 'auto')""",
            (user_id, role_id, today, start_hour, end_hour, hours_worked, current_rate)
        )
        await db.commit()

# --- Функция add_manual_shift ---
async def add_manual_shift(user_id: int, role_id: int, shift_date_str: str, hours_worked: float):
    current_rate = await _get_current_role_rate(role_id)  # Берем ставку на момент записи

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "INSERT INTO shifts (user_id, role_id, shift_date, hours_worked, rate_at_time, entry_type, start_time, end_time) " # Добавим start/end_time = -1
            "VALUES (?, ?, ?, ?, 'manual_adjustment', -1, -1)",
            (user_id, role_id, shift_date_str, hours_worked, current_rate)
        )
        await db.commit()

# --- Функции отчетов ---
async def get_all_users() -> list[tuple[int, str]]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, first_name FROM users ORDER BY first_name") as cursor:
            return await cursor.fetchall()

async def get_user_shifts_report(user_id: int, start_date: date, end_date: date) -> Tuple[float, float, Dict[str, Dict]]:
    query = """
        SELECT
            s.shift_date, s.start_time, s.end_time, s.hours_worked, s.entry_type,
            s.rate_at_time, r.name as role_name, r.rate as role_rate
        FROM shifts s
        LEFT JOIN roles r ON s.role_id = r.role_id
        WHERE s.user_id = ? AND s.shift_date BETWEEN ? AND ?
        ORDER BY s.shift_date, s.start_time
    """
    report_by_role: Dict[str, Dict] = {}
    grand_total_hours = 0.0
    grand_total_earnings = 0.0
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, (user_id, start_date.isoformat(), end_date.isoformat())) as cursor:
            async for row in cursor:
                shift_date_str, start_hour, end_hour, hours, entry_type, rate, role_name = row
                role_name = role_name or "Неизвестная роль"
                rate = rate or 0.0 # Используем ставку ИЗ СМЕНЫ
                earnings = hours * rate
                grand_total_hours += hours
                grand_total_earnings += earnings
                if role_name not in report_by_role:
                    report_by_role[role_name] = {'hours': 0.0, 'rate': rate, 'earnings': 0.0, 'shifts': []}
                report_by_role[role_name]['hours'] += hours
                report_by_role[role_name]['earnings'] += earnings
                if entry_type == 'auto':
                    shift_str = f"• {shift_date_str}: {start_hour}:00 - {end_hour}:00 ({hours:.1f} ч.)"
                else: # manual_adjustment
                    hours_str = f"+{hours:.1f}" if hours > 0 else f"{hours:.1f}"
                    shift_str = f"• {shift_date_str}: [Корр.] ({hours_str} ч.)"
                report_by_role[role_name]['shifts'].append(shift_str)
    for role in report_by_role:
        report_by_role[role]['hours'] = round(report_by_role[role]['hours'], 2)
        report_by_role[role]['earnings'] = round(report_by_role[role]['earnings'], 2)
    return round(grand_total_hours, 2), round(grand_total_earnings, 2), report_by_role

async def get_month_hours_for_user(user_id: int, month_start_date: date) -> float:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT SUM(hours_worked) FROM shifts WHERE user_id = ? AND shift_date >= ?",
            (user_id, month_start_date.isoformat())
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result and result[0] is not None else 0.0

async def get_summary_report(start_date: date, end_date: date, entry_types: Optional[List[str]] = None) -> List[Dict]:
    query = """
        SELECT
            u.first_name AS user_name,
            r.name AS role_name,
            SUM(s.hours_worked) AS role_total_hours,
            SUM(s.hours_worked * s.rate_at_time) AS role_total_earnings
        FROM shifts AS s
        JOIN users AS u ON s.user_id = u.user_id
        LEFT JOIN roles AS r ON s.role_id = r.role_id
        WHERE s.shift_date BETWEEN ? AND ?
    """
    params = [start_date.isoformat(), end_date.isoformat()]
    if entry_types:
        placeholders = ', '.join('?' * len(entry_types))
        query += f" AND s.entry_type IN ({placeholders})"
        params.extend(entry_types)
    query += """
        GROUP BY u.user_id, u.first_name, r.role_id, r.name
        ORDER BY u.first_name, r.name
    """
    summary_by_user: Dict[str, Dict] = {}
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, params) as cursor:
            async for row in cursor:
                user_name, role_name, role_total_hours, role_total_earnings = row
                role_name = role_name or "Неизвестная роль"
                if user_name not in summary_by_user:
                    summary_by_user[user_name] = {'user_name': user_name, 'total_hours': 0.0, 'total_earnings': 0.0, 'roles': {}}
                summary_by_user[user_name]['total_hours'] += role_total_hours
                summary_by_user[user_name]['total_earnings'] += role_total_earnings
                if role_name not in summary_by_user[user_name]['roles']:
                     summary_by_user[user_name]['roles'][role_name] = {'hours': 0.0, 'earnings': 0.0}
                summary_by_user[user_name]['roles'][role_name]['hours'] += role_total_hours
                summary_by_user[user_name]['roles'][role_name]['earnings'] += role_total_earnings
    result_list = []
    for user_data in summary_by_user.values():
        user_data['total_hours'] = round(user_data['total_hours'], 2)
        user_data['total_earnings'] = round(user_data['total_earnings'], 2)
        for role_data in user_data['roles'].values():
            role_data['hours'] = round(role_data['hours'], 2)
            role_data['earnings'] = round(role_data['earnings'], 2)
        result_list.append(user_data)
    result_list.sort(key=lambda x: x['total_hours'], reverse=True)
    return result_list

# --- Функция delete_user ---
async def delete_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        # Каскадное удаление само удалит user_roles, shifts, active_shifts
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_month_hours_for_user_role(user_id: int, role_id: int, month_start_date: date) -> float:
    """Считает сумму часов пользователя по КОНКРЕТНОЙ РОЛИ с начала месяца."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            """SELECT SUM(hours_worked)
               FROM shifts
               WHERE user_id = ? AND role_id = ? AND shift_date >= ?""",
            (user_id, role_id, month_start_date.isoformat())
        ) as cursor:
            result = await cursor.fetchone()
            # Возвращаем 0.0, если записей нет или сумма NULL
            return result[0] if result and result[0] is not None else 0.0