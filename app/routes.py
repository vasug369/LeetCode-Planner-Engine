"""FastAPI API routes and dashboard serving."""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import date, datetime
import os
import logging
import sys

from app.database import (
    get_db, init_db, get_solved_count, get_problem_count,
    get_topic_stats, get_schedule_for_date, mark_schedule_complete,
    clear_schedule_for_date, get_current_streak, get_longest_streak,
    get_all_problems, get_unsolved_problems, get_solved_problems,
)
from app.scraper import load_sde_sheet
from app.scheduler import sync_leetcode_progress
from app.planner import generate_daily_plan, get_plan_summary
from app.email_service import send_daily_email
from app.config import settings


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Setup logging
logger = logging.getLogger("uvicorn")


def register_routes(app: FastAPI):
    """Register all API routes on the FastAPI app."""

    @app.on_event("startup")
    async def startup():
        init_db()
        load_sde_sheet()

    # ── Dashboard ────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse("dashboard.html", {"request": request})

    # ── Stats API ────────────────────────────────────────────

    @app.get("/api/stats")
    async def get_stats():
        db = get_db()
        try:
            total = get_problem_count(db)
            solved = get_solved_count(db)
            unsolved = total - solved
            streak = get_current_streak(db)
            longest = get_longest_streak(db)

            # Difficulty breakdown
            all_problems = get_all_problems(db)
            solved_problems = get_solved_problems(db)

            diff_total = {"Easy": 0, "Medium": 0, "Hard": 0}
            diff_solved = {"Easy": 0, "Medium": 0, "Hard": 0}

            for p in all_problems:
                diff_total[p.difficulty] = diff_total.get(p.difficulty, 0) + 1
            for p in solved_problems:
                diff_solved[p.difficulty] = diff_solved.get(p.difficulty, 0) + 1

            return {
                "total": total,
                "solved": solved,
                "unsolved": unsolved,
                "progress_pct": round((solved / total) * 100, 1) if total > 0 else 0,
                "current_streak": streak,
                "longest_streak": longest,
                "difficulty": {
                    "total": diff_total,
                    "solved": diff_solved,
                },
                "username": settings.LEETCODE_USERNAME,
            }
        finally:
            db.close()

    # ── Topic Stats ──────────────────────────────────────────

    @app.get("/api/topics")
    async def get_topics():
        db = get_db()
        try:
            stats = get_topic_stats(db)
            return {"topics": stats}
        finally:
            db.close()

    # ── Today's Schedule ─────────────────────────────────────

    @app.get("/api/schedule/today")
    async def get_today_schedule():
        db = get_db()
        try:
            schedule = get_schedule_for_date(db, date.today())
            items = []
            for entry in schedule:
                items.append({
                    "id": entry.id,
                    "title": entry.problem.title,
                    "slug": entry.problem.slug,
                    "difficulty": entry.problem.difficulty,
                    "topic": entry.problem.topic,
                    "url": entry.problem.leetcode_url,
                    "category": entry.category,
                    "expected_time": entry.expected_time,
                    "status": entry.completion_status,
                })
            return {"date": date.today().isoformat(), "schedule": items}
        finally:
            db.close()

    # ── Generate Plan ────────────────────────────────────────

    @app.post("/api/generate-plan")
    async def generate_plan():
        db = get_db()
        try:
            # Clear existing schedule for today
            clear_schedule_for_date(db, date.today())

            plan = generate_daily_plan(db, date.today())
            summary = get_plan_summary(plan)
            return {"status": "success", "plan": summary}
        finally:
            db.close()

    # ── Sync LeetCode ────────────────────────────────────────

    @app.post("/api/sync")
    async def sync_progress():
        db = get_db()
        try:
            result = sync_leetcode_progress(db)
            return result
        finally:
            db.close()

    # ── Send Email ───────────────────────────────────────────

    @app.post("/api/send-email")
    async def trigger_email():
        db = get_db()
        try:
            schedule = get_schedule_for_date(db, date.today())
            if not schedule:
                # Generate plan first
                plan = generate_daily_plan(db, date.today())
            else:
                plan = [
                    {"problem": e.problem, "category": e.category,
                     "expected_time": e.expected_time}
                    for e in schedule
                ]

            summary = get_plan_summary(plan)
            result = send_daily_email(summary)
            return result
        finally:
            db.close()

    # ── Mark Complete ────────────────────────────────────────

    @app.post("/api/schedule/{entry_id}/complete")
    async def complete_entry(entry_id: int):
        db = get_db()
        try:
            entry = mark_schedule_complete(db, entry_id, "completed")
            if not entry:
                raise HTTPException(status_code=404, detail="Schedule entry not found")
            return {"status": "success", "entry_id": entry_id, "new_status": "completed"}
        finally:
            db.close()

    @app.post("/api/schedule/{entry_id}/skip")
    async def skip_entry(entry_id: int):
        db = get_db()
        try:
            entry = mark_schedule_complete(db, entry_id, "skipped")
            if not entry:
                raise HTTPException(status_code=404, detail="Schedule entry not found")
            return {"status": "success", "entry_id": entry_id, "new_status": "skipped"}
        finally:
            db.close()

    # ── Health Check ─────────────────────────────────────────

    @app.get("/ping")
    @app.head("/ping")
    async def ping():
        """Minimal health check for cron/uptime monitors."""
        return JSONResponse(content={"ping": "pong"}, status_code=200)

    # ── External Cron Endpoints (For Render/Vercel) ──────────

    def verify_cron_secret(req: Request):
        auth = req.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ")[1]
            if token == settings.CRON_SECRET:
                return True
        secret_param = req.query_params.get("secret")
        if secret_param == settings.CRON_SECRET:
            return True
        raise HTTPException(status_code=401, detail="Unauthorized CRON trigger")

    @app.get("/api/cron/sync")
    @app.post("/api/cron/sync")
    @app.head("/api/cron/sync")
    async def cron_sync(request: Request, background_tasks: BackgroundTasks):
        verify_cron_secret(request)
        
        def do_sync():
            logger.info("🕒 [Cron] Starting background sync task...")
            db = get_db()
            try:
                result = sync_leetcode_progress(db)
                logger.info(f"✅ Background sync finished: {result}")
            except Exception as e:
                logger.error(f"❌ Error in background sync: {e}")
            finally:
                db.close()
                sys.stdout.flush()

        background_tasks.add_task(do_sync)
        return JSONResponse(content={"ok": True}, status_code=202)

    @app.get("/api/cron/daily")
    @app.post("/api/cron/daily")
    @app.head("/api/cron/daily")
    async def cron_daily(request: Request, background_tasks: BackgroundTasks):
        verify_cron_secret(request)
        
        def do_daily_task():
            logger.info("🕒 [Cron] Starting background daily planner task...")
            db = get_db()
            try:
                plan = generate_daily_plan(db, date.today())
                summary = get_plan_summary(plan)
                logger.info(f"📋 Generated plan with {summary['total_problems']} problems.")
                if settings.EMAIL_TO and settings.SMTP_USER and settings.SMTP_PASSWORD:
                    logger.info(f"📧 Sending email to {settings.EMAIL_TO}...")
                    send_daily_email(summary)
                else:
                    logger.warning("⚠️ Email skipped: Missing SMTP settings in environment.")
                logger.info("🏁 Background daily task finished successfully.")
            except Exception as e:
                logger.error(f"❌ Error in background daily task: {e}")
            finally:
                db.close()
                sys.stdout.flush()

        background_tasks.add_task(do_daily_task)
        return JSONResponse(content={"ok": True}, status_code=202)
