from fastapi import APIRouter
from app.db.database import get_config_db, update_config_db, get_stats_db, get_live_requests_db

admin_router = APIRouter(prefix="/api/admin")

@admin_router.get("/stats")
async def get_stats():
    return await get_stats_db()

@admin_router.get("/config")
async def get_config():
    return await get_config_db()

@admin_router.post("/config")
async def update_config(new_config: dict):
    await update_config_db(new_config)
    return {"status": "success"}

@admin_router.get("/requests/live")
async def get_live_requests():
    return await get_live_requests_db()
