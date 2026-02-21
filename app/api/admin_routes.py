from fastapi import APIRouter
import time
from app.db.database import pool, get_config_db, update_config_db

admin_router = APIRouter(prefix="/api/admin")

@admin_router.get("/stats")
async def get_stats():
    async with pool.acquire() as db:
        row = await db.fetchrow("SELECT COUNT(*) as count, AVG(latency_ms) as avg_lat, SUM(fallback_triggered) as fallbacks FROM metrics WHERE timestamp > $1", time.time()-3600)
        
        rows = await db.fetch("SELECT model_used, COUNT(*) as c FROM metrics GROUP BY model_used ORDER BY c DESC")
        
        return {
            "req_last_hour": row["count"] or 0,
            "avg_latency": round(row["avg_lat"] or 0, 2) if row["avg_lat"] else 0,
            "fallback_count": row["fallbacks"] or 0,
            "model_distribution": [{"model": m["model_used"], "count": m["c"]} for m in rows]
        }

@admin_router.get("/config")
async def get_config():
    return await get_config_db()

@admin_router.post("/config")
async def update_config(new_config: dict):
    await update_config_db(new_config)
    return {"status": "success"}

@admin_router.get("/requests/live")
async def get_live_requests():
    async with pool.acquire() as db:
        rows = await db.fetch("""
            SELECT id, timestamp, session_id, model_used, latency_ms, fallback_triggered, status 
            FROM metrics ORDER BY timestamp DESC LIMIT 20
        """)
        return [{"id": r["id"], "time": r["timestamp"], "session": r["session_id"], "model": r["model_used"], "latency": r["latency_ms"], "fallback": bool(r["fallback_triggered"]), "status": r["status"]} for r in rows]
