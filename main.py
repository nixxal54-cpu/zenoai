import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.db.database import init_db
from app.api.routes import router as chat_router
from app.api.admin_routes import admin_router

# Initialize FastAPI (Disabling Swagger UI as requested)
app = FastAPI(
    title="ZenoAi",
    docs_url=None, 
    redoc_url=None
)

# Startup Event to initialize DB
@app.on_event("startup")
async def startup_event():
    await init_db()
    print("🚀 ZenoAi Backend Initialized & Database Mounted")

# Mount API Routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(admin_router)

# Mount Admin UI Webpage
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    # Read the admin.html file and serve it
    ui_path = os.path.join(os.path.dirname(__file__), "app", "ui", "admin.html")
    with open(ui_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return html_content

if __name__ == "__main__":
    import uvicorn
    # Run the server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)