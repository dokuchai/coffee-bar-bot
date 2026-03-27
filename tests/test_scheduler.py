"""
Unit tests for scheduler/jobs.py.

All external dependencies (Bot, database calls, i18n) are mocked with
AsyncMock / MagicMock so tests run without a real Telegram connection or DB.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound

import database
from scheduler.jobs import remind_end_shift, cron_auto_close_shifts


def _make_bot():
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


def _make_i18n(text="⏰ Reminder text"):
    i18n = MagicMock()
    i18n.get = MagicMock(return_value=text)
    return i18n


# ---------------------------------------------------------------------------
# remind_end_shift
# ---------------------------------------------------------------------------

class TestRemindEndShift:
    async def test_no_active_shifts_sends_nothing(self):
        bot = _make_bot()
        i18n = _make_i18n()
        with patch("database.get_users_with_active_shifts", new=AsyncMock(return_value=[])):
            await remind_end_shift(bot, i18n)
        bot.send_message.assert_not_called()

    async def test_sends_reminder_to_users_with_todays_shifts(self):
        bot = _make_bot()
        i18n = _make_i18n("⏰ Завершите смену")
        today = "2024-01-15"
        active = [
            (101, 1, f"{today}T09:00:00+01:00"),  # today
            (102, 2, f"{today}T10:00:00+01:00"),  # today
        ]
        with patch("database.get_users_with_active_shifts", new=AsyncMock(return_value=active)), \
             patch("database.get_today", return_value=MagicMock(isoformat=lambda: today)):
            await remind_end_shift(bot, i18n)
        assert bot.send_message.call_count == 2
        bot.send_message.assert_any_call(101, "⏰ Завершите смену")
        bot.send_message.assert_any_call(102, "⏰ Завершите смену")

    async def test_skips_shifts_from_previous_days(self):
        bot = _make_bot()
        i18n = _make_i18n()
        today = "2024-01-15"
        yesterday = "2024-01-14"
        active = [
            (101, 1, f"{today}T09:00:00+01:00"),   # today → remind
            (102, 2, f"{yesterday}T22:00:00+01:00"), # yesterday → skip
        ]
        with patch("database.get_users_with_active_shifts", new=AsyncMock(return_value=active)), \
             patch("database.get_today", return_value=MagicMock(isoformat=lambda: today)):
            await remind_end_shift(bot, i18n)
        assert bot.send_message.call_count == 1
        bot.send_message.assert_called_once_with(101, i18n.get("reminder_end_shift", locale="ru"))

    async def test_forbidden_error_is_swallowed(self):
        bot = _make_bot()
        i18n = _make_i18n()
        today = "2024-01-15"
        active = [(101, 1, f"{today}T09:00:00+01:00")]
        bot.send_message.side_effect = TelegramForbiddenError(method=MagicMock(), message="Forbidden")
        with patch("database.get_users_with_active_shifts", new=AsyncMock(return_value=active)), \
             patch("database.get_today", return_value=MagicMock(isoformat=lambda: today)):
            # Should not raise
            await remind_end_shift(bot, i18n)

    async def test_not_found_error_is_swallowed(self):
        bot = _make_bot()
        i18n = _make_i18n()
        today = "2024-01-15"
        active = [(101, 1, f"{today}T09:00:00+01:00")]
        bot.send_message.side_effect = TelegramNotFound(method=MagicMock(), message="Not Found")
        with patch("database.get_users_with_active_shifts", new=AsyncMock(return_value=active)), \
             patch("database.get_today", return_value=MagicMock(isoformat=lambda: today)):
            await remind_end_shift(bot, i18n)

    async def test_i18n_failure_uses_fallback_text(self):
        bot = _make_bot()
        i18n = MagicMock()
        i18n.get = MagicMock(side_effect=Exception("i18n broken"))
        today = "2024-01-15"
        active = [(101, 1, f"{today}T09:00:00+01:00")]
        with patch("database.get_users_with_active_shifts", new=AsyncMock(return_value=active)), \
             patch("database.get_today", return_value=MagicMock(isoformat=lambda: today)):
            await remind_end_shift(bot, i18n)
        # Fallback message contains key Russian text
        call_args = bot.send_message.call_args[0]
        assert "Напоминание" in call_args[1]


# ---------------------------------------------------------------------------
# cron_auto_close_shifts
# ---------------------------------------------------------------------------

class TestCronAutoCloseShifts:
    async def test_no_open_shifts_sends_nothing(self, tmp_path):
        bot = _make_bot()
        i18n = _make_i18n()
        db_file = str(tmp_path / "empty.db")
        with patch("database.DB_NAME", db_file), \
             patch("scheduler.jobs.db.DB_NAME", db_file):
            import database as db_mod
            db_mod.DB_NAME = db_file
            await db_mod.init_db()
            await cron_auto_close_shifts(bot, i18n)
        bot.send_message.assert_not_called()

    def _make_aiosqlite_connect_mock(self, rows):
        """
        Build a mock for aiosqlite.connect(...) whose conn.execute(...)
        returns a synchronous async-context-manager yielding `rows`.

        aiosqlite uses:  async with conn.execute("...") as c:
        so conn.execute must return an object (not a coroutine) that has
        async __aenter__/__aexit__.
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchall = AsyncMock(return_value=rows)
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=False)

        mock_conn = MagicMock()
        # execute() must return the cursor synchronously
        mock_conn.execute = MagicMock(return_value=mock_cursor)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        return mock_conn

    async def test_closes_open_shifts_and_notifies(self):
        bot = _make_bot()
        i18n = _make_i18n()
        fake_result = (90, "09:00:00", "10:30:00")
        mock_conn = self._make_aiosqlite_connect_mock(rows=[(101,)])
        with patch("database.close_shift", new=AsyncMock(return_value=fake_result)) as mock_close, \
             patch("database.get_now", return_value=datetime(2024, 1, 15, 20, 30, 0, tzinfo=database.TZ)), \
             patch("aiosqlite.connect", return_value=mock_conn):
            await cron_auto_close_shifts(bot, i18n)

        mock_close.assert_awaited_once()
        bot.send_message.assert_called_once()
        msg_text = bot.send_message.call_args[0][1]
        assert "автоматически закрыта" in msg_text
        assert "09:00:00" in msg_text
        assert "10:30:00" in msg_text

    async def test_close_shift_none_result_skips_notification(self):
        """If close_shift returns None (already closed), no message is sent."""
        bot = _make_bot()
        i18n = _make_i18n()
        mock_conn = self._make_aiosqlite_connect_mock(rows=[(101,)])
        with patch("database.close_shift", new=AsyncMock(return_value=None)), \
             patch("database.get_now", return_value=datetime(2024, 1, 15, 20, 30, 0, tzinfo=database.TZ)), \
             patch("aiosqlite.connect", return_value=mock_conn):
            await cron_auto_close_shifts(bot, i18n)
        bot.send_message.assert_not_called()

    async def test_send_message_exception_does_not_crash(self):
        """Notification failure should be caught; job should complete."""
        bot = _make_bot()
        bot.send_message.side_effect = Exception("Network error")
        i18n = _make_i18n()
        fake_result = (60, "09:00:00", "10:00:00")
        mock_conn = self._make_aiosqlite_connect_mock(rows=[(101,)])
        with patch("database.close_shift", new=AsyncMock(return_value=fake_result)), \
             patch("database.get_now", return_value=datetime(2024, 1, 15, 20, 30, 0, tzinfo=database.TZ)), \
             patch("aiosqlite.connect", return_value=mock_conn):
            # Should not raise
            await cron_auto_close_shifts(bot, i18n)
