from fastapi import APIRouter
from app.core.config import config_manager
from app.db.database import DB_PATH
import aiosqlite

admin_router = APIRouter(prefix="/api/admin")

@admin_router.get("/stats")
async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        # Aggregations
        cursor = await db.execute("SELECT COUNT(*), AVG(latency_ms), SUM(fallback_triggered) FROM metrics WHERE timestamp > ?", (time.time()-3600,))
        h1_data = await cursor.fetchone()
        
        cursor = await db.execute("SELECT model_used, COUNT(*) as c FROM metrics GROUP BY model_used ORDER BY c DESC")
        models = await cursor.fetchall()
        
        return {
            "req_last_hour": h1_data[0] or 0,
            "avg_latency": round(h1_data[1] or 0, 2),
            "fallback_count": h1_data[2] or 0,
            "model_distribution": [{"model": m[0], "count": m[1]} for m in models]
        }

@admin_router.get("/config")
async def get_config():
    return config_manager.get()

@admin_router.post("/config")
async def update_config(new_config: dict):
    config_manager.update(new_config)
    return {"status": "success"}

@admin_router.get("/requests/live")
async def get_live_requests():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, timestamp, session_id, model_used, latency_ms, fallback_triggered, status 
            FROM metrics ORDER BY timestamp DESC LIMIT 20
        """)
        rows = await cursor.fetchall()
        return [{"id": r[0], "time": r[1], "session": r[2], "model": r[3], "latency": r[4], "fallback": bool(r[5]), "status": r[6]} for r in rows]
