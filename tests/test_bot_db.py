"""Unit tests for bot SQLite database operations."""

import pytest
from x2t.bot.database.db import Database


@pytest.mark.asyncio
async def test_database_lifecycle(tmp_path):
    db_file = tmp_path / "test_bot.sqlite3"
    db = Database(db_path=str(db_file))

    # 1. Initialize schema
    await db.init_db()

    # 2. Upsert user
    await db.upsert_user(user_id=1001, username="testuser", full_name="Test User")
    await db.upsert_user(user_id=1002, username="anotheruser", full_name="Another User")

    # 3. Record downloads
    await db.record_download(user_id=1001, tweet_id="12345", media_count=2)
    await db.record_download(user_id=1001, tweet_id="67890", media_count=1)

    # 4. Check stats
    stats = await db.get_stats()
    assert stats["total_users"] == 2
    assert stats["total_downloads"] == 3
    assert stats["active_24h"] == 2

    # 5. Check user IDs for broadcast
    user_ids = await db.get_all_user_ids()
    assert set(user_ids) == {1001, 1002}

    # 6. Close database connection
    await db.close()
