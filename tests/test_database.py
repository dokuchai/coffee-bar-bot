"""
Unit / integration tests for database.py.

All tests that hit SQLite use the `db` fixture from conftest.py which
provides a fresh temp file and patches database.DB_NAME automatically.
Tests for pure functions need no fixtures.
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import patch

import database


# ---------------------------------------------------------------------------
# Pure-function tests – no DB, no mocks needed
# ---------------------------------------------------------------------------

class TestFormatMinutesToStr:
    def test_zero(self):
        assert database.format_minutes_to_str(0) == "0 ч. 0 м."

    def test_exact_hours(self):
        assert database.format_minutes_to_str(120) == "2 ч. 0 м."

    def test_mixed(self):
        assert database.format_minutes_to_str(95) == "1 ч. 35 м."

    def test_negative(self):
        assert database.format_minutes_to_str(-90) == "-1 ч. 30 м."

    def test_less_than_hour(self):
        assert database.format_minutes_to_str(45) == "0 ч. 45 м."


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

class TestUserManagement:
    async def test_add_and_get_user(self, db):
        await database.add_or_update_user(1, "user1", "Alice")
        users = await database.get_all_users()
        assert (1, "Alice") in users

    async def test_update_existing_user(self, db):
        await database.add_or_update_user(1, "old_name", "Alice")
        await database.add_or_update_user(1, "new_name", "Alice Updated")
        users = await database.get_all_users()
        # Only one record for user_id=1, with updated name
        names = [u[1] for u in users if u[0] == 1]
        assert names == ["Alice Updated"]

    async def test_get_user_by_id_exists(self, db):
        await database.add_or_update_user(42, "bob", "Bob")
        name = await database.get_user_by_id(42)
        assert name == "Bob"

    async def test_get_user_by_id_missing(self, db):
        name = await database.get_user_by_id(9999)
        assert name is None

    async def test_delete_user(self, db):
        await database.add_or_update_user(5, "del", "ToDelete")
        await database.delete_user(5)
        assert await database.get_user_by_id(5) is None

    async def test_set_and_get_locale(self, db):
        await database.add_or_update_user(10, "u", "User")
        await database.set_user_locale(10, "en")
        locale = await database.get_user_locale(10)
        assert locale == "en"

    async def test_get_locale_missing_user(self, db):
        locale = await database.get_user_locale(9999)
        assert locale is None


# ---------------------------------------------------------------------------
# Role management
# ---------------------------------------------------------------------------

class TestRoles:
    async def test_get_roles_returns_defaults(self, db):
        roles = await database.get_roles()
        role_ids = [r[0] for r in roles]
        assert 1 in role_ids and 2 in role_ids and 3 in role_ids

    async def test_check_user_has_roles_false_initially(self, db):
        await database.add_or_update_user(20, "u", "User")
        assert await database.check_user_has_roles(20) is False

    async def test_set_and_check_user_roles(self, db):
        await database.add_or_update_user(20, "u", "User")
        await database.set_user_roles(20, [1, 3])
        assert await database.check_user_has_roles(20) is True

    async def test_get_user_roles(self, db):
        await database.add_or_update_user(20, "u", "User")
        await database.set_user_roles(20, [2])
        roles = await database.get_user_roles(20)
        assert len(roles) == 1
        assert roles[0][0] == 2  # role_id

    async def test_set_user_roles_replaces_previous(self, db):
        await database.add_or_update_user(21, "u2", "User2")
        await database.set_user_roles(21, [1, 2])
        await database.set_user_roles(21, [3])
        roles = await database.get_user_roles(21)
        assert [r[0] for r in roles] == [3]


# ---------------------------------------------------------------------------
# Shift lifecycle
# ---------------------------------------------------------------------------

class TestShiftLifecycle:
    async def _setup_user_with_role(self, user_id=100):
        await database.add_or_update_user(user_id, "worker", "Worker")
        await database.set_user_roles(user_id, [1])
        return user_id

    async def test_no_active_shift_initially(self, db):
        await self._setup_user_with_role()
        assert await database.is_shift_active(100) is False

    async def test_shift_becomes_active_after_start(self, db):
        await self._setup_user_with_role()
        with patch("database.get_now", return_value=datetime(2024, 1, 15, 9, 0, 0, tzinfo=database.TZ)), \
             patch("database.get_today", return_value=date(2024, 1, 15)):
            await database.record_shift_start(100, 1)
        assert await database.is_shift_active(100) is True

    async def test_close_shift_returns_minutes(self, db):
        await self._setup_user_with_role()
        start = datetime(2024, 1, 15, 9, 0, 0, tzinfo=database.TZ)
        end = datetime(2024, 1, 15, 10, 30, 0, tzinfo=database.TZ)
        with patch("database.get_now", return_value=start), \
             patch("database.get_today", return_value=date(2024, 1, 15)):
            await database.record_shift_start(100, 1)
        with patch("database.get_now", return_value=end):
            result = await database.close_shift(100)
        assert result is not None
        mins, t_start, t_end = result
        assert mins == 90
        assert t_start == "09:00:00"
        assert t_end == "10:30:00"

    async def test_close_shift_no_active_returns_none(self, db):
        await self._setup_user_with_role()
        result = await database.close_shift(100)
        assert result is None

    async def test_is_shift_inactive_after_close(self, db):
        await self._setup_user_with_role()
        start = datetime(2024, 1, 15, 9, 0, 0, tzinfo=database.TZ)
        end = datetime(2024, 1, 15, 11, 0, 0, tzinfo=database.TZ)
        with patch("database.get_now", return_value=start), \
             patch("database.get_today", return_value=date(2024, 1, 15)):
            await database.record_shift_start(100, 1)
        with patch("database.get_now", return_value=end):
            await database.close_shift(100)
        assert await database.is_shift_active(100) is False


# ---------------------------------------------------------------------------
# Shift status
# ---------------------------------------------------------------------------

class TestGetShiftStatus:
    async def test_status_none_when_no_shifts(self, db):
        await database.add_or_update_user(200, "u", "U")
        await database.set_user_roles(200, [1])
        status = await database.get_shift_status(200)
        assert status == "none"

    async def test_status_active_when_shift_open(self, db):
        await database.add_or_update_user(200, "u", "U")
        await database.set_user_roles(200, [1])
        with patch("database.get_now", return_value=datetime(2024, 1, 15, 9, 0, 0, tzinfo=database.TZ)), \
             patch("database.get_today", return_value=date(2024, 1, 15)):
            await database.record_shift_start(200, 1)
        status = await database.get_shift_status(200)
        assert status == "active"

    async def test_status_finished_all_when_all_roles_used(self, db):
        await database.add_or_update_user(200, "u", "U")
        await database.set_user_roles(200, [1])
        today = date(2024, 1, 15)
        start = datetime(2024, 1, 15, 9, 0, 0, tzinfo=database.TZ)
        end = datetime(2024, 1, 15, 10, 0, 0, tzinfo=database.TZ)
        with patch("database.get_now", return_value=start), \
             patch("database.get_today", return_value=today):
            await database.record_shift_start(200, 1)
        with patch("database.get_now", return_value=end), \
             patch("database.get_today", return_value=today):
            await database.close_shift(200)
        with patch("database.get_today", return_value=today):
            status = await database.get_shift_status(200)
        assert status == "finished_all"


# ---------------------------------------------------------------------------
# get_used_role_ids_today
# ---------------------------------------------------------------------------

class TestGetUsedRoleIdsToday:
    async def test_empty_when_no_closed_shifts(self, db):
        await database.add_or_update_user(300, "u", "U")
        await database.set_user_roles(300, [1])
        with patch("database.get_today", return_value=date(2024, 1, 15)):
            used = await database.get_used_role_ids_today(300)
        assert used == []

    async def test_returns_role_after_close(self, db):
        await database.add_or_update_user(300, "u", "U")
        await database.set_user_roles(300, [1])
        today = date(2024, 1, 15)
        start = datetime(2024, 1, 15, 9, 0, 0, tzinfo=database.TZ)
        end = datetime(2024, 1, 15, 10, 0, 0, tzinfo=database.TZ)
        with patch("database.get_now", return_value=start), \
             patch("database.get_today", return_value=today):
            await database.record_shift_start(300, 1)
        with patch("database.get_now", return_value=end):
            await database.close_shift(300)
        with patch("database.get_today", return_value=today):
            used = await database.get_used_role_ids_today(300)
        assert 1 in used


# ---------------------------------------------------------------------------
# get_month_hours_for_user
# ---------------------------------------------------------------------------

class TestGetMonthHours:
    async def test_zero_when_no_shifts(self, db):
        await database.add_or_update_user(400, "u", "U")
        mins = await database.get_month_hours_for_user(400, date(2024, 1, 1))
        assert mins == 0

    async def test_sums_minutes_in_period(self, db):
        await database.add_or_update_user(400, "u", "U")
        await database.set_user_roles(400, [1])
        today = date(2024, 1, 15)
        start = datetime(2024, 1, 15, 9, 0, 0, tzinfo=database.TZ)
        end = datetime(2024, 1, 15, 10, 0, 0, tzinfo=database.TZ)  # 60 minutes
        with patch("database.get_now", return_value=start), \
             patch("database.get_today", return_value=today):
            await database.record_shift_start(400, 1)
        with patch("database.get_now", return_value=end):
            await database.close_shift(400)
        mins = await database.get_month_hours_for_user(400, date(2024, 1, 1))
        assert mins == 60


# ---------------------------------------------------------------------------
# add_manual_adjustment
# ---------------------------------------------------------------------------

class TestManualAdjustment:
    async def test_manual_entry_recorded(self, db):
        await database.add_or_update_user(500, "u", "U")
        await database.set_user_roles(500, [2])
        with patch("database.get_now", return_value=datetime(2024, 1, 15, 12, 0, 0, tzinfo=database.TZ)), \
             patch("database.get_today", return_value=date(2024, 1, 15)):
            await database.add_manual_adjustment(500, 2, 45)
        mins = await database.get_month_hours_for_user(500, date(2024, 1, 1))
        assert mins == 45

    async def test_manual_shift_not_counted_as_active(self, db):
        await database.add_or_update_user(500, "u", "U")
        with patch("database.get_now", return_value=datetime(2024, 1, 15, 12, 0, 0, tzinfo=database.TZ)), \
             patch("database.get_today", return_value=date(2024, 1, 15)):
            await database.add_manual_adjustment(500, 1, 30)
        assert await database.is_shift_active(500) is False


# ---------------------------------------------------------------------------
# get_users_with_active_shifts
# ---------------------------------------------------------------------------

class TestGetUsersWithActiveShifts:
    async def test_returns_open_shifts(self, db):
        await database.add_or_update_user(600, "u", "U")
        await database.set_user_roles(600, [1])
        with patch("database.get_now", return_value=datetime(2024, 1, 15, 9, 0, 0, tzinfo=database.TZ)), \
             patch("database.get_today", return_value=date(2024, 1, 15)):
            await database.record_shift_start(600, 1)
        active = await database.get_users_with_active_shifts()
        user_ids = [row[0] for row in active]
        assert 600 in user_ids

    async def test_closed_shifts_not_included(self, db):
        await database.add_or_update_user(601, "u2", "U2")
        await database.set_user_roles(601, [1])
        start = datetime(2024, 1, 15, 9, 0, 0, tzinfo=database.TZ)
        end = datetime(2024, 1, 15, 11, 0, 0, tzinfo=database.TZ)
        with patch("database.get_now", return_value=start), \
             patch("database.get_today", return_value=date(2024, 1, 15)):
            await database.record_shift_start(601, 1)
        with patch("database.get_now", return_value=end):
            await database.close_shift(601)
        active = await database.get_users_with_active_shifts()
        user_ids = [row[0] for row in active]
        assert 601 not in user_ids
