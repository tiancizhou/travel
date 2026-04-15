import aiosqlite
import json
from datetime import datetime

DB_PATH = "travel.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                start_lng REAL NOT NULL,
                start_lat REAL NOT NULL,
                end_lng REAL NOT NULL,
                end_lat REAL NOT NULL,
                distance INTEGER,
                duration INTEGER,
                guide TEXT
            )
        """)
        await db.commit()


async def insert_query(
    start_lng, start_lat, end_lng, end_lat, distance, duration, guide
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO query_logs
               (created_at, start_lng, start_lat, end_lng, end_lat, distance, duration, guide)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                start_lng,
                start_lat,
                end_lng,
                end_lat,
                distance,
                duration,
                guide,
            ),
        )
        await db.commit()


async def get_history(limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM query_logs ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
