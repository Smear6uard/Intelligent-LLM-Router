import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "router.db")

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS requests (
            id TEXT PRIMARY KEY,
            prompt TEXT NOT NULL,
            task_type TEXT NOT NULL,
            complexity REAL NOT NULL,
            confidence REAL NOT NULL,
            model TEXT NOT NULL,
            was_routed INTEGER NOT NULL DEFAULT 1,
            response_text TEXT,
            latency_ms INTEGER,
            tokens_used INTEGER,
            cost_cents REAL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests(created_at);
        CREATE INDEX IF NOT EXISTS idx_requests_model ON requests(model);
        CREATE INDEX IF NOT EXISTS idx_requests_task_type ON requests(task_type);

        CREATE TABLE IF NOT EXISTS ab_tests (
            id TEXT PRIMARY KEY,
            prompt TEXT NOT NULL,
            task_type TEXT NOT NULL,
            complexity REAL NOT NULL,
            models TEXT NOT NULL,
            winner_model TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_ab_tests_created_at ON ab_tests(created_at);

        CREATE TABLE IF NOT EXISTS ab_results (
            id TEXT PRIMARY KEY,
            ab_test_id TEXT NOT NULL REFERENCES ab_tests(id),
            model TEXT NOT NULL,
            response_text TEXT,
            latency_ms INTEGER,
            tokens_used INTEGER,
            cost_cents REAL
        );

        CREATE INDEX IF NOT EXISTS idx_ab_results_ab_test_id ON ab_results(ab_test_id);
    """)
    await db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


async def insert_request(data: dict):
    db = await get_db()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data.keys())
    await db.execute(f"INSERT INTO requests ({cols}) VALUES ({placeholders})", data)
    await db.commit()


async def insert_ab_test(data: dict):
    db = await get_db()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data.keys())
    await db.execute(f"INSERT INTO ab_tests ({cols}) VALUES ({placeholders})", data)
    await db.commit()


async def insert_ab_result(data: dict):
    db = await get_db()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data.keys())
    await db.execute(f"INSERT INTO ab_results ({cols}) VALUES ({placeholders})", data)
    await db.commit()


async def fetch_all(query: str, params: dict | None = None):
    db = await get_db()
    cursor = await db.execute(query, params or {})
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def fetch_one(query: str, params: dict | None = None):
    db = await get_db()
    cursor = await db.execute(query, params or {})
    row = await cursor.fetchone()
    return dict(row) if row else None


async def execute(query: str, params: dict | None = None):
    db = await get_db()
    await db.execute(query, params or {})
    await db.commit()
