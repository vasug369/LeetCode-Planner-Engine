"""
LeetCode Planner Engine — Main Application

FastAPI server with dashboard, API routes, and auto-scheduling.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from app.routes import register_routes
from app.config import settings
from app.database import get_db, init_db, get_schedule_for_date
from app.scraper import load_sde_sheet
from app.scheduler import sync_leetcode_progress
from app.planner import generate_daily_plan, get_plan_summary
from app.email_service import send_daily_email

def auto_sync_job():
    """Background job to automatically sync LeetCode progress."""
    print(f"\n[Auto-Sync] {datetime.now()} - Starting scheduled sync...")
    db = get_db()
    try:
        sync_leetcode_progress(db)
        print(f"[Auto-Sync] {datetime.now()} - Sync complete.")
    finally:
        db.close()

def auto_daily_planner_job():
    """Background job to generate plan and send daily email."""
    print(f"\n[Auto-Plan] {datetime.now()} - Generating daily plan and sending email...")
    db = get_db()
    try:
        # Generate or get plan
        plan = generate_daily_plan(db)
        summary = get_plan_summary(plan)
        
        # Send email
        if settings.EMAIL_TO and settings.SMTP_USER and settings.SMTP_PASSWORD:
            send_daily_email(summary)
            print(f"[Auto-Plan] {datetime.now()} - Daily email sent successfully.")
        else:
            print(f"[Auto-Plan] {datetime.now()} - Skipped email (credentials not configured).")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and data on startup
    init_db()
    load_sde_sheet()
    
    # Initialize Scheduler
    scheduler = BackgroundScheduler()
    
    # 1. Auto Sync Job (e.g. every 30 mins)
    scheduler.add_job(
        auto_sync_job,
        trigger=IntervalTrigger(minutes=settings.AUTO_SYNC_INTERVAL_MINUTES),
        id="auto_sync",
        name="Auto Sync LeetCode Progress",
        replace_existing=True,
    )
    
    # 2. Daily Plan & Email Job
    hour, minute = map(int, settings.DAILY_EMAIL_TIME.split(":"))
    scheduler.add_job(
        auto_daily_planner_job,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="auto_daily_plan",
        name="Auto Generate Plan and Email",
        replace_existing=True,
    )
    
    scheduler.start()
    print("\n⏰ Autonomous Scheduler Started:")
    print(f"   - Sync: Every {settings.AUTO_SYNC_INTERVAL_MINUTES} mins")
    print(f"   - Plan & Email: Daily at {settings.DAILY_EMAIL_TIME}")
    
    yield
    
    scheduler.shutdown()
    print("\n⏰ Autonomous Scheduler Stopped")

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
