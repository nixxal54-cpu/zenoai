import asyncpg
import json
import uuid
import time
from app.core.config import settings

pool = None

async def init_db():
    global pool
    # Connect to Cloud PostgreSQL
    pool = await asyncpg.create_pool(settings.DATABASE_URL)
    
    async with pool.acquire() as db:
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS app_config (
                id INTEGER PRIMARY KEY,
                config_data JSONB
            )
        """)
        
        existing = await db.fetchval("SELECT COUNT(*) FROM app_config WHERE id = 1")
        if existing == 0:
            default_config = {
              "default_model": "google/gemini-2.0-flash-lite-preview-02-05:free",
              "models": [
                {"id": "google/gemini-2.0-flash-lite-preview-02-05:free", "enabled": True, "timeout": 20},
                {"id": "google/gemma-2-9b-it:free", "enabled": True, "timeout": 20},
                {"id": "meta-llama/llama-3-8b-instruct:free", "enabled": True, "timeout": 15},
                {"id": "mistralai/mistral-7b-instruct:free", "enabled": True, "timeout": 15}
              ],
              "fallback_order": [
                "google/gemini-2.0-flash-lite-preview-02-05:free",
                "google/gemma-2-9b-it:free",
                "meta-llama/llama-3-8b-instruct:free",
                "mistralai/mistral-7b-instruct:free"
              ],
              "retry_count": 2,
              "max_tokens": 1024,
              "memory_window": 10,
              "system_prompt": "You are ZenoAi, an advanced AI backend."
            }
            await db.execute("INSERT INTO app_config (id, config_data) VALUES (1, $1)", json.dumps(default_config))

async def get_config_db():
    async with pool.acquire() as db:
        row = await db.fetchval("SELECT config_data FROM app_config WHERE id = 1")
        config = json.loads(row) if isinstance(row, str) else row
        print(f"[Config] Type: {type(config)} | Keys: {list(config.keys()) if isinstance(config, dict) else 'NOT A DICT'}")
        print(f"[Config] fallback_order: {config.get('fallback_order')}")
        return config

async def update_config_db(new_config: dict):
    async with pool.acquire() as db:
        await db.execute("UPDATE app_config SET config_data = $1 WHERE id = 1", json.dumps(new_config))

async def create_session() -> str:
    sess_id = str(uuid.uuid4())
    async with pool.acquire() as db:
        await db.execute("INSERT INTO sessions (id, created_at) VALUES ($1, $2)", sess_id, time.time())
    return sess_id

async def save_message(session_id: str, role: str, content: str):
    async with pool.acquire() as db:
        await db.execute("INSERT INTO messages (id, session_id, role, content, timestamp) VALUES ($1, $2, $3, $4, $5)",
                         str(uuid.uuid4()), session_id, role, content, time.time())

async def get_memory(session_id: str, limit: int):
    async with pool.acquire() as db:
        rows = await db.fetch(
            "SELECT role, content FROM messages WHERE session_id = $1 ORDER BY timestamp DESC LIMIT $2", 
            session_id, limit
        )
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

async def log_metric(session_id: str, model: str, latency: float, fallback: bool, tokens: int, status: str, error: str = ""):
    async with pool.acquire() as db:
        await db.execute("""
            INSERT INTO metrics (id, timestamp, session_id, model_used, latency_ms, fallback_triggered, tokens, status, error_msg)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, str(uuid.uuid4()), time.time(), session_id, model, latency, int(fallback), tokens, status, error)

# --- NEW HELPER FUNCTIONS FOR ADMIN STATS ---

async def get_stats_db():
    async with pool.acquire() as db:
        # Get stats for the last hour
        row = await db.fetchrow("SELECT COUNT(*) as count, AVG(latency_ms) as avg_lat, SUM(fallback_triggered) as fallbacks FROM metrics WHERE timestamp > $1", time.time()-3600)
        # Get model usage counts
        rows = await db.fetch("SELECT model_used, COUNT(*) as c FROM metrics GROUP BY model_used ORDER BY c DESC")
        
        return {
            "req_last_hour": row["count"] or 0,
            "avg_latency": round(row["avg_lat"] or 0, 2) if row["avg_lat"] else 0,
            "fallback_count": row["fallbacks"] or 0,
            "model_distribution": [{"model": m["model_used"], "count": m["c"]} for m in rows]
        }

async def get_live_requests_db():
    async with pool.acquire() as db:
        rows = await db.fetch("""
            SELECT id, timestamp, session_id, model_used, latency_ms, fallback_triggered, status 
            FROM metrics ORDER BY timestamp DESC LIMIT 20
        """)
        return [{"id": r["id"], "time": r["timestamp"], "session": r["session_id"], "model": r["model_used"], "latency": r["latency_ms"], "fallback": bool(r["fallback_triggered"]), "status": r["status"]} for r in rows]
