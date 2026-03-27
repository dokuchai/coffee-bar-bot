"""
Unit tests for filters.py.

MagicI18nFilter compares message.text to the translated value of a key.
All Telegram types are mocked – no network or bot needed.
"""
import pytest
from unittest.mock import MagicMock

from filters import MagicI18nFilter


class TestMagicI18nFilter:
    def _make_message(self, text):
        msg = MagicMock()
        msg.text = text
        return msg

    def _translator(self, translation: str):
        """Returns a callable that always returns the given translation."""
        return MagicMock(return_value=translation)

    async def test_exact_match_returns_true(self):
        f = MagicI18nFilter("button_start")
        msg = self._make_message("Начать смену")
        t = self._translator("Начать смену")
        assert await f(msg, t) is True

    async def test_wrong_text_returns_false(self):
        f = MagicI18nFilter("button_start")
        msg = self._make_message("Завершить смену")
        t = self._translator("Начать смену")
        assert await f(msg, t) is False

    async def test_empty_message_text_returns_false(self):
        f = MagicI18nFilter("button_start")
        msg = self._make_message(None)
        t = self._translator("Начать смену")
        assert await f(msg, t) is False

    async def test_partial_match_returns_false(self):
        f = MagicI18nFilter("button_start")
        msg = self._make_message("Начать")
        t = self._translator("Начать смену")
        assert await f(msg, t) is False

    async def test_case_sensitive(self):
        f = MagicI18nFilter("button_start")
        msg = self._make_message("начать смену")
        t = self._translator("Начать смену")
        assert await f(msg, t) is False

    async def test_translator_called_with_key(self):
        """Verify the translator is called with the correct i18n key."""
        f = MagicI18nFilter("some_key")
        msg = self._make_message("value")
        t = self._translator("value")
        await f(msg, t)
        t.assert_called_once_with("some_key")
