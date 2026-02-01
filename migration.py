import sqlite3
import logging

DB_NAME = 'coffee_bot.db'

logging.basicConfig(level=logging.INFO)


def migrate():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        logging.info("Начало миграции...")

        # 1. Проверяем, существует ли старая таблица
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shifts'")
        if not cursor.fetchone():
            logging.error("Таблица shifts не найдена. Возможно, миграция уже проведена.")
            return

        # 2. Переименовываем старую таблицу
        cursor.execute("ALTER TABLE shifts RENAME TO shifts_old")
        logging.info("Старая таблица переименована в shifts_old")

        # 3. Создаем новую таблицу (end_time может быть NULL, минуты — INTEGER)
        cursor.execute('''
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
        logging.info("Новая таблица shifts создана")

        # 4. Переносим данные с конвертацией
        # Предполагаем: hours_worked был в часах (float), rate_at_time был в часах (float)
        # Мы умножаем часы на 60 и округляем. Ставку делим на 60 и храним как строку.
        cursor.execute('''
            INSERT INTO shifts (
                user_id, role_id, shift_date, start_time, end_time, 
                minutes_worked, rate_at_time, entry_type
            )
            SELECT 
                user_id, 
                role_id, 
                shift_date, 
                COALESCE(start_time, shift_date || 'T08:30:00'), -- Заглушка, если не было времени
                end_time,
                CAST(COALESCE(hours_worked, 0) * 60 AS INTEGER),
                CAST(ROUND(CAST(rate_at_time AS REAL) / 60, 2) AS TEXT),
                COALESCE(entry_type, 'auto')
            FROM shifts_old
        ''')

        logging.info(f"Перенесено {cursor.rowcount} записей")

        # 5. Если была таблица active_shifts — её можно просто удалить,
        # так как теперь активные смены живут в основной таблице
        cursor.execute("DROP TABLE IF EXISTS active_shifts")
        logging.info("Удалена старая вспомогательная таблица active_shifts")

        # 6. Финальный коммит
        conn.commit()
        logging.info("Миграция успешно завершена! Теперь можно удалять shifts_old вручную.")

    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка при миграции: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()