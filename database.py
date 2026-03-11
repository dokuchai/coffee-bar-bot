import logging
import aiosqlite
from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple, Dict
from decimal import Decimal, ROUND_HALF_UP
import pytz

# Настраиваем часовой пояс
TZ = pytz.timezone('Europe/Belgrade')


def get_now():
    return datetime.now(TZ)


def get_today():
    return get_now().date()


DB_NAME = 'coffee_bot.db'

# СТАВКА ЗА 1 МИНУТУ (Например: 11.0 RSD)
ROLES_DATA = [
    (1, 'Помощник повара', "6.7"),
    (2, 'Повар', "6.7"),
    (3, 'Бариста', "6.2")
]


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        # 1. ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, 
                username TEXT, 
                first_name TEXT,
                locale TEXT DEFAULT 'ru'
            )
        ''')

        try:
            await db.execute("ALTER TABLE users ADD COLUMN locale TEXT DEFAULT 'ru'")
            await db.commit()
            print("✅ База данных обновлена: добавлена колонка locale")
        except aiosqlite.OperationalError:
            # Если колонка уже есть, SQLite выдаст ошибку, которую мы просто игнорируем
            pass

        # 2. ТАБЛИЦА РОЛЕЙ
        await db.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                role_id INTEGER PRIMARY KEY, 
                name TEXT UNIQUE NOT NULL, 
                rate TEXT NOT NULL
            )
        ''')

        # 3. ТАБЛИЦА СМЕН (Единая)
        # Проверяем структуру: если end_time обязателен (NOT NULL), пересоздаем
        async with db.execute("PRAGMA table_info(shifts)") as cursor:
            columns = await cursor.fetchall()
            is_dirty = False
            if columns:
                end_time_col = next((c for c in columns if c[1] == 'end_time'), None)
                if end_time_col and end_time_col[3] == 1:
                    is_dirty = True

            if is_dirty or not columns:
                logging.info("Миграция таблицы shifts...")
                if columns:
                    await db.execute("ALTER TABLE shifts RENAME TO shifts_old")

                await db.execute('''
                    CREATE TABLE shifts (
                        shift_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL, 
                        role_id INTEGER NOT NULL,
                        shift_date TEXT NOT NULL, 
                        start_time TEXT NOT NULL, 
                        end_time TEXT, 
                        minutes_worked INTEGER DEFAULT 0, 
                        rate_at_time TEXT NOT NULL, 
                        entry_type TEXT NOT NULL DEFAULT 'auto'
                    )
                ''')
                if columns:
                    # Пытаемся перенести что можно (старые часы станут минутами)
                    await db.execute('''
                        INSERT INTO shifts (user_id, role_id, shift_date, start_time, end_time, minutes_worked, rate_at_time, entry_type)
                        SELECT user_id, role_id, shift_date, start_time, end_time, 
                               CAST(COALESCE(hours_worked, 0) * 60 AS INTEGER), 
                               CAST(rate_at_time AS TEXT), entry_type 
                        FROM shifts_old
                    ''')
                    await db.execute("DROP TABLE shifts_old")

        # 4. ТАБЛИЦА СВЯЗИ РОЛЕЙ
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER NOT NULL, 
                role_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, role_id)
            )
        ''')

        # Обновляем ставки из конфига
        for rid, name, rate in ROLES_DATA:
            await db.execute('''
                INSERT INTO roles (role_id, name, rate) VALUES (?, ?, ?)
                ON CONFLICT(role_id) DO UPDATE SET rate = excluded.rate, name = excluded.name
            ''', (rid, name, rate))

        await db.commit()


# --- ЛОГИКА СМЕН ---

async def get_used_role_ids_today(user_id: int) -> List[int]:
    """Возвращает список ID ролей, по которым сегодня уже были ЗАКРЫТЫЕ смены."""
    today = get_today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                "SELECT role_id FROM shifts WHERE user_id = ? AND shift_date = ? AND end_time IS NOT NULL",
                (user_id, today)
        ) as c:
            rows = await c.fetchall()
            return [row[0] for row in rows]


async def get_shift_status(user_id: int) -> str:
    """Определяет статус, используя проверку активности."""
    # 1. Сначала проверяем, идет ли смена прямо сейчас
    if await is_shift_active(user_id):
        return 'active'

    # 2. Если активной нет, проверяем, остались ли неиспользованные роли на сегодня
    user_roles = await get_user_roles(user_id)
    used_roles = await get_used_role_ids_today(user_id)

    # Если список отработанных ролей меньше, чем список всех ролей юзера
    if len(used_roles) < len(user_roles):
        return 'none'

    # Если всё отработано
    return 'finished_all'


async def is_shift_active(user_id: int) -> bool:
    """ПРЯМОЙ запрос в базу без вызова других функций."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                "SELECT 1 FROM shifts WHERE user_id = ? AND end_time IS NULL LIMIT 1",
                (user_id,)
        ) as c:
            res = await c.fetchone()
            return res is not None


async def record_shift_start(user_id: int, role_id: int):
    now_iso = get_now().isoformat()
    today = get_today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT rate FROM roles WHERE role_id = ?", (role_id,)) as rc:
            rate_str = (await rc.fetchone())[0]
        await db.execute('''
            INSERT INTO shifts (user_id, role_id, shift_date, start_time, rate_at_time, entry_type)
            VALUES (?, ?, ?, ?, ?, 'auto')
        ''', (user_id, role_id, today, now_iso, rate_str))
        await db.commit()


async def close_shift(user_id: int, end_dt: Optional[datetime] = None):
    now = get_now()  # Aware datetime (с часовым поясом)
    now_iso = now.isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                "SELECT shift_id, start_time FROM shifts WHERE user_id = ? AND end_time IS NULL LIMIT 1",
                (user_id,)
        ) as c:
            row = await c.fetchone()
            if not row:
                return None
            sid, start_iso = row
            start_dt = datetime.fromisoformat(start_iso)
            end_dt_naive = now.replace(tzinfo=None)
            start_dt_naive = start_dt.replace(tzinfo=None)
            diff = end_dt_naive - start_dt_naive
            mins = int(diff.total_seconds() // 60)
            if mins < 0:
                mins = 0
            await db.execute(
                "UPDATE shifts SET end_time = ?, minutes_worked = ? WHERE user_id = ? AND end_time IS NULL",
                (now_iso, mins, user_id)
            )
            await db.commit()
            t_start = start_dt.strftime("%H:%M:%S")
            t_end = now.strftime("%H:%M:%S")
            return mins, t_start, t_end


def format_minutes_to_str(total_minutes: int) -> str:
    """Вспомогательная функция для красивого вывода времени (в т.ч. отрицательного)."""
    abs_mins = abs(total_minutes)
    h, m = divmod(abs_mins, 60)
    sign = "-" if total_minutes < 0 else ""
    return f"{sign}{h} ч. {m} м."



async def get_user_shifts_report(user_id: int, start_date: date, end_date: date):
    query = """
            SELECT 
                s.shift_date, 
                s.start_time, 
                s.end_time, 
                s.minutes_worked, 
                s.rate_at_time, 
                r.name, 
                s.entry_type
            FROM shifts s
            LEFT JOIN roles r ON s.role_id = r.role_id
            WHERE s.user_id = ? AND s.shift_date BETWEEN ? AND ?
            ORDER BY s.shift_date ASC, s.start_time ASC
        """
    total_min, total_money, shifts_list = 0, Decimal('0.00'), []
    current_time = get_now()
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, (user_id, start_date.isoformat(), end_date.isoformat())) as cursor:
            async for row in cursor:
                s_date, s_t, e_t, mins, rate_str, r_name, entry_type = row
                rate = Decimal(rate_str)
                role_label = r_name if r_name else "???"
                if entry_type == 'manual' or str(s_t).startswith('manual'):
                    t_range = "[Корр.]"
                elif e_t is None:
                    # Если T в строке нет (мало ли), берем как есть, иначе режем время
                    t_start = s_t.split('T')[-1][:5] if 'T' in s_t else s_t[:5]
                    t_range = f"{t_start} - 🟢"
                else:
                    t_start = s_t.split('T')[-1][:5] if 'T' in s_t else s_t[:5]
                    t_end = e_t.split('T')[-1][:5] if 'T' in e_t else e_t[:5]
                    t_range = "[Корр.]" if t_start == "manua" else f"{t_start} - {t_end}"

                if e_t is None and entry_type != 'manual':
                    # "Живой" расчет для открытой смены
                    start_dt = datetime.fromisoformat(s_t).replace(tzinfo=None)
                    now_naive = current_time.replace(tzinfo=None)
                    diff = now_naive - start_dt
                    display_mins = int(diff.total_seconds() // 60)
                    if display_mins < 0: display_mins = 0
                    time_label = "⚡️ <b>В процессе:</b>"
                else:
                    # Для закрытых и КОРРЕКТИРОВОК берем готовые минуты из базы
                    display_mins = mins
                    time_label = ""

                earn = (Decimal(display_mins) * rate).quantize(Decimal('0.01'), ROUND_HALF_UP)

                # Суммируем только то, что влияет на итог
                total_min += display_mins
                total_money += earn

                h_str = format_minutes_to_str(display_mins)

                shifts_list.append(
                    f"📅 {s_date} | {t_range} | {role_label}\n"
                    f"      └ {time_label} {h_str} | {earn} RSD"
                )

    return total_min, total_money, shifts_list


# --- ВСПОМОГАТЕЛЬНЫЕ ---

async def get_user_roles(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                "SELECT r.role_id, r.name, r.rate FROM user_roles ur JOIN roles r ON ur.role_id = r.role_id WHERE ur.user_id = ?",
                (user_id,)) as c:
            return await c.fetchall()


async def get_roles():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT role_id, name, rate FROM roles") as c: return await c.fetchall()


async def set_user_roles(user_id: int, role_ids: List[int]):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
        await db.executemany("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                             [(user_id, rid) for rid in role_ids])
        await db.commit()


async def add_or_update_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name",
            (user_id, username or '', first_name or ''))
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, first_name FROM users") as c: return await c.fetchall()


async def get_user_by_id(user_id: int) -> Optional[str]:
    """Возвращает first_name пользователя по user_id."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT first_name FROM users WHERE user_id = ?", (user_id,)) as c:
            row = await c.fetchone()
            return row[0] if row else None


async def get_month_hours_for_user(user_id: int, m_start: date) -> int:
    """Возвращает количество МИНУТ за месяц."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT SUM(minutes_worked) FROM shifts WHERE user_id = ? AND shift_date >= ?",
                              (user_id, m_start.isoformat())) as c:
            res = await c.fetchone()
            return res[0] if res and res[0] else 0


async def add_manual_adjustment(user_id: int, role_id: int, minutes: int):
    now_iso = get_now().isoformat()
    today_iso = get_today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT rate FROM roles WHERE role_id = ?", (role_id,)) as rc:
            rate_str = (await rc.fetchone())[0]
        await db.execute("""
            INSERT INTO shifts (user_id, role_id, shift_date, start_time, end_time, minutes_worked, rate_at_time, entry_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'manual')
        """, (user_id, role_id, today_iso, now_iso, now_iso, minutes, rate_str))
        await db.commit()


async def delete_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()


async def check_user_has_roles(user_id: int) -> bool:
    """Проверяет, привязана ли к пользователю хотя бы одна роль."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                "SELECT 1 FROM user_roles WHERE user_id = ? LIMIT 1",
                (user_id,)
        ) as cursor:
            res = await cursor.fetchone()
            return res is not None


async def get_total_summary_report(start_date: date, end_date: date):
    """Возвращает общую сумму и время по всем сотрудникам за период."""
    query = """
        SELECT u.first_name, s.start_time, s.end_time, s.minutes_worked, s.rate_at_time, s.entry_type
        FROM shifts s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.shift_date BETWEEN ? AND ?
    """

    user_totals = {}  # { "Имя": {"mins": 0, "money": Decimal} }
    grand_total_mins = 0
    grand_total_money = Decimal('0.00')
    now_naive = get_now().replace(tzinfo=None)

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, (start_date.isoformat(), end_date.isoformat())) as cursor:
            async for row in cursor:
                name, s_t, e_t, mins, rate_str, entry_type = row
                rate = Decimal(rate_str)

                if name not in user_totals:
                    user_totals[name] = {"mins": 0, "money": Decimal('0.00')}

                # Логика расчета (как в детальном отчете)
                if e_t is None and entry_type != 'manual':
                    start_dt = datetime.fromisoformat(s_t).replace(tzinfo=None)
                    current_mins = int((now_naive - start_dt).total_seconds() // 60)
                    if current_mins < 0: current_mins = 0
                else:
                    current_mins = mins

                current_money = (Decimal(current_mins) * rate).quantize(Decimal('0.01'), ROUND_HALF_UP)

                # Плюсуем сотруднику
                user_totals[name]["mins"] += current_mins
                user_totals[name]["money"] += current_money

                # Плюсуем в общий итог
                grand_total_mins += current_mins
                grand_total_money += current_money

    return user_totals, grand_total_mins, grand_total_money


# --- Функции для планировщика и логики смен ---
async def get_users_with_active_shifts():
    """Возвращает список всех открытых смен: [(user_id, role_id, start_time_str), ...]"""
    query = "SELECT user_id, role_id, start_time FROM shifts WHERE end_time IS NULL"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query) as cursor:
            return await cursor.fetchall()


async def set_user_locale(user_id: int, locale: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET locale = ? WHERE user_id = ?", (locale, user_id))
        await db.commit()


async def get_user_locale(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT locale FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None
