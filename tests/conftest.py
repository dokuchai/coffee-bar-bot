"""
Shared fixtures for all tests.

The `db` fixture patches database.DB_NAME to a temp file and runs init_db(),
so every test function gets a clean, isolated SQLite database.
"""
import pytest
import sys
import os
from unittest.mock import patch

# Make the project root importable when running pytest from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
async def db(tmp_path):
    """Provide a fresh, initialised in-file SQLite database for each test."""
    db_file = str(tmp_path / "test_coffee.db")
    with patch("database.DB_NAME", db_file):
        import database
        # Re-patch DB_NAME inside the already-imported module too
        original = database.DB_NAME
        database.DB_NAME = db_file
        await database.init_db()
        yield db_file
        database.DB_NAME = original
