import aiosqlite
import json
import uuid
import time

DB_PATH = "zenoai_store.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, created_at REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id TEXT PRIMARY KEY, timestamp REAL, session_id TEXT, 
                model_used TEXT, latency_ms REAL, fallback_triggered INTEGER, 
                tokens REAL, status TEXT, error_msg TEXT
            )
        """)
        await db.commit()

async def create_session() -> str:
    sess_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO sessions (id, created_at) VALUES (?, ?)", (sess_id, time.time()))
        await db.commit()
    return sess_id

async def save_message(session_id: str, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO messages (id, session_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (str(uuid.uuid4()), session_id, role, content, time.time()))
        await db.commit()

async def get_memory(session_id: str, limit: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?", 
            (session_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

async def log_metric(session_id: str, model: str, latency: float, fallback: bool, tokens: int, status: str, error: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO metrics (id, timestamp, session_id, model_used, latency_ms, fallback_triggered, tokens, status, error_msg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), time.time(), session_id, model, latency, int(fallback), tokens, status, error))
        await db.commit()
