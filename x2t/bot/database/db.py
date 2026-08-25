"""Async SQLite database manager for x2t bot."""

import datetime
from pathlib import Path
from typing import Dict, List, Optional
import aiosqlite


class Database:
    """Handles async SQLite operations for tracking bot users and download statistics."""

    def __init__(self, db_path: str = "bot_database.sqlite3"):
        self.db_path = db_path

    async def init_db(self):
        """Initialize database schema and tables."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_downloads INTEGER DEFAULT 0
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    tweet_id TEXT,
                    media_count INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def upsert_user(self, user_id: int, username: Optional[str], full_name: Optional[str]):
        """Insert or update user activity."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, full_name, joined_at, last_active_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    last_active_at = excluded.last_active_at
                """,
                (user_id, username, full_name, now, now),
            )
            await db.commit()

    async def record_download(self, user_id: int, tweet_id: str, media_count: int):
        """Record a successful media download for user and stats."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE users
                SET total_downloads = total_downloads + ?,
                    last_active_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (media_count, user_id),
            )
            await db.execute(
                """
                INSERT INTO downloads_log (user_id, tweet_id, media_count)
                VALUES (?, ?, ?)
                """,
                (user_id, tweet_id, media_count),
            )
            await db.commit()

    async def get_stats(self) -> Dict[str, int]:
        """Fetch general stats for admin panel."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cur:
                total_users = (await cur.fetchone())[0]

            async with db.execute("SELECT COALESCE(SUM(total_downloads), 0) FROM users") as cur:
                total_downloads = (await cur.fetchone())[0]

            async with db.execute(
                "SELECT COUNT(*) FROM users WHERE last_active_at >= datetime('now', '-1 day')"
            ) as cur:
                active_24h = (await cur.fetchone())[0]

            return {
                "total_users": total_users,
                "total_downloads": total_downloads,
                "active_24h": active_24h,
            }

    async def get_all_user_ids(self) -> List[int]:
        """Get all user IDs for admin broadcast."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id FROM users") as cur:
                rows = await cur.fetchall()
                return [row[0] for row in rows]
