"""
LeetCode Planner Engine — Main Application

FastAPI server with dashboard, API routes, and cron-triggered scheduling.
Scheduling is handled externally via cron-job.org (no internal scheduler).
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from app.routes import register_routes
from app.database import init_db
from app.scraper import load_sde_sheet


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize DB and load SDE sheet data."""
    init_db()
    load_sde_sheet()
    print("\n✅ Startup complete — DB initialized, SDE sheet loaded.")
    print("   Scheduling is handled by cron-job.org (no internal scheduler).")

    yield

    print("\n👋 Shutting down.")


app = FastAPI(
    title="LeetCode Planner Engine",
    description="Personal LeetCode preparation planner for the Striver SDE Sheet",
    version="1.0.0",
    lifespan=lifespan,
)

# Register all API routes
register_routes(app)

if __name__ == "__main__":
    print("\n🚀 LeetCode Planner Engine starting...")
    print("   Dashboard: http://localhost:8000")
    print("   API Docs:  http://localhost:8000/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
