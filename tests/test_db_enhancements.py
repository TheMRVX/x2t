"""Unit tests for SQLite WAL connection pool, user history, profile filter persistence, and settings storage."""

import pytest
from x2t.bot.database.db import Database


@pytest.mark.asyncio
async def test_database_persistent_connection_and_wal(tmp_path):
    """Test database persistent connection reuse, WAL mode, and table initialization."""
    db_file = str(tmp_path / "test_wal.sqlite3")
    db = Database(db_path=db_file)

    await db.init_db()
    conn1 = await db.get_connection()
    conn2 = await db.get_connection()

    # Verify same persistent connection is reused
    assert conn1 is conn2

    # Verify WAL journal mode
    async with conn1.execute("PRAGMA journal_mode;") as cur:
        journal_mode = (await cur.fetchone())[0]
        assert journal_mode.upper() == "WAL"

    await db.close()


@pytest.mark.asyncio
async def test_database_user_history(tmp_path):
    """Test recording downloads and retrieving user download history."""
    db_file = str(tmp_path / "test_history.sqlite3")
    db = Database(db_path=db_file)
    await db.init_db()

    user_id = 99887766
    await db.upsert_user(user_id=user_id, username="test_user", full_name="Test User")

    # Record 3 downloads
    await db.record_download(user_id=user_id, tweet_id="11111", media_count=1)
    await db.record_download(user_id=user_id, tweet_id="22222", media_count=4)
    await db.record_download(user_id=user_id, tweet_id="33333", media_count=2)

    history = await db.get_user_history(user_id=user_id, limit=2)
    assert len(history) == 2
    # Verify latest is first (DESC order)
    assert history[0]["tweet_id"] == "33333"
    assert history[0]["media_count"] == 2
    assert history[1]["tweet_id"] == "22222"

    all_history = await db.get_user_history(user_id=user_id, limit=5)
    assert len(all_history) == 3

    await db.close()


@pytest.mark.asyncio
async def test_database_profile_filter_persistence(tmp_path):
    """Test saving and retrieving user profile filter options."""
    db_file = str(tmp_path / "test_filters.sqlite3")
    db = Database(db_path=db_file)
    await db.init_db()

    user_id = 12345
    username = "ElonMusk"
    filter_json = '{"include_videos":true,"include_photos":false,"limit":25}'

    # Verify initially none
    assert await db.get_profile_filter(user_id, username) is None

    # Save and verify
    await db.save_profile_filter(user_id, username, filter_json)
    retrieved = await db.get_profile_filter(user_id, username)
    assert retrieved == filter_json

    # Test case-insensitivity of username lookup
    retrieved_lower = await db.get_profile_filter(user_id, "elonmusk")
    assert retrieved_lower == filter_json

    # Update filter and verify
    updated_json = '{"include_videos":false,"include_photos":true,"limit":0}'
    await db.save_profile_filter(user_id, username, updated_json)
    assert await db.get_profile_filter(user_id, username) == updated_json

    await db.close()


@pytest.mark.asyncio
async def test_database_app_settings(tmp_path):
    """Test saving and getting application configuration values in SQLite."""
    db_file = str(tmp_path / "test_settings.sqlite3")
    db = Database(db_path=db_file)
    await db.init_db()

    assert await db.get_setting("twitter_auth_token") is None

    await db.set_setting("twitter_auth_token", "sample_secret_token_123")
    assert await db.get_setting("twitter_auth_token") == "sample_secret_token_123"

    await db.set_setting("is_private", "false")
    assert await db.get_setting("is_private") == "false"

    await db.close()
