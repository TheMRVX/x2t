"""Async SQLite database manager with persistent WAL connection pool and settings storage."""

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite


class Database:
    """Handles persistent async SQLite operations for tracking bot users, history, and settings."""

    def __init__(self, db_path: str = "bot_database.sqlite3"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def get_connection(self) -> aiosqlite.Connection:
        """Get or initialize the persistent async SQLite connection with WAL mode enabled."""
        if self._conn is None:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = await aiosqlite.connect(self.db_path)
            # Enable WAL mode for high concurrent throughput & robustness
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.execute("PRAGMA synchronous=NORMAL;")
            await self._conn.execute("PRAGMA busy_timeout=5000;")
            await self._conn.commit()
        return self._conn

    async def close(self):
        """Cleanly close the persistent database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def init_db(self):
        """Initialize database schema and required tables."""
        conn = await self.get_connection()
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_downloads INTEGER DEFAULT 0
            );
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS downloads_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tweet_id TEXT,
                media_count INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile_filters (
                user_id INTEGER,
                username TEXT,
                filter_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, username)
            );
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await conn.commit()

    async def upsert_user(self, user_id: int, username: Optional[str], full_name: Optional[str]):
        """Insert or update user activity."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = await self.get_connection()
        await conn.execute(
            """
            INSERT INTO users (user_id, username, full_name, joined_at, last_active_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                last_active_at = excluded.last_active_at;
            """,
            (user_id, username, full_name, now, now),
        )
        await conn.commit()

    async def record_download(self, user_id: int, tweet_id: str, media_count: int):
        """Record a successful media download for user and stats."""
        conn = await self.get_connection()
        await conn.execute(
            """
            UPDATE users
            SET total_downloads = total_downloads + ?,
                last_active_at = CURRENT_TIMESTAMP
            WHERE user_id = ?;
            """,
            (media_count, user_id),
        )
        await conn.execute(
            """
            INSERT INTO downloads_log (user_id, tweet_id, media_count)
            VALUES (?, ?, ?);
            """,
            (user_id, tweet_id, media_count),
        )
        await conn.commit()

    async def get_user_history(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch latest downloads for a user."""
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT tweet_id, media_count, timestamp
            FROM downloads_log
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?;
            """,
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
            return [
                {
                    "tweet_id": row[0],
                    "media_count": row[1],
                    "timestamp": row[2],
                }
                for row in rows
            ]

    async def save_profile_filter(self, user_id: int, username: str, filter_json: str):
        """Persist user's profile filter options across restarts."""
        conn = await self.get_connection()
        await conn.execute(
            """
            INSERT INTO user_profile_filters (user_id, username, filter_json, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, username) DO UPDATE SET
                filter_json = excluded.filter_json,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (user_id, username.lower(), filter_json),
        )
        await conn.commit()

    async def get_profile_filter(self, user_id: int, username: str) -> Optional[str]:
        """Load user's saved profile filter options."""
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT filter_json
            FROM user_profile_filters
            WHERE user_id = ? AND username = ?;
            """,
            (user_id, username.lower()),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

    async def set_setting(self, key: str, value: str):
        """Set a persistent application configuration value."""
        conn = await self.get_connection()
        await conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (key, value),
        )
        await conn.commit()

    async def get_setting(self, key: str) -> Optional[str]:
        """Get a persistent application configuration value."""
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT value FROM app_settings WHERE key = ?;",
            (key,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

    async def get_stats(self) -> Dict[str, int]:
        """Fetch general stats for admin panel."""
        conn = await self.get_connection()
        async with conn.execute("SELECT COUNT(*) FROM users;") as cur:
            total_users = (await cur.fetchone())[0]

        async with conn.execute("SELECT COALESCE(SUM(total_downloads), 0) FROM users;") as cur:
            total_downloads = (await cur.fetchone())[0]

        async with conn.execute(
            "SELECT COUNT(*) FROM users WHERE last_active_at >= datetime('now', '-1 day');"
        ) as cur:
            active_24h = (await cur.fetchone())[0]

        return {
            "total_users": total_users,
            "total_downloads": total_downloads,
            "active_24h": active_24h,
        }

    async def get_all_user_ids(self) -> List[int]:
        """Get all user IDs for admin broadcast."""
        conn = await self.get_connection()
        async with conn.execute("SELECT user_id FROM users;") as cur:
            rows = await cur.fetchall()
            return [row[0] for row in rows]
