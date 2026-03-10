"""
Daily Runner Script — Run this via cron or Task Scheduler.

Performs the following steps:
1. Syncs LeetCode progress
2. Generates daily plan
3. Sends email notification

Usage:
    python daily_run.py
    python daily_run.py --no-email
    python daily_run.py --sync-only
"""

import argparse
from datetime import date

from app.database import init_db, get_db
from app.scraper import load_sde_sheet
from app.scheduler import sync_leetcode_progress
from app.planner import generate_daily_plan, get_plan_summary
from app.email_service import send_daily_email
from app.config import settings


def main():
    parser = argparse.ArgumentParser(description="LeetCode Planner Engine — Daily Runner")
    parser.add_argument("--no-email", action="store_true", help="Skip sending email")
    parser.add_argument("--sync-only", action="store_true", help="Only sync LeetCode progress")
    parser.add_argument("--plan-only", action="store_true", help="Only generate plan (no sync, no email)")
    parser.add_argument("--email-only", action="store_true", help="Only send email with existing plan")
    args = parser.parse_args()

    print("=" * 60)
    print(f"🚀 LeetCode Planner Engine — Daily Run")
    print(f"   Date: {date.today().strftime('%A, %B %d, %Y')}")
    print(f"   User: {settings.LEETCODE_USERNAME or 'Not configured'}")
    print("=" * 60)

    # Initialize
    init_db()
    load_sde_sheet()
    db = get_db()

    try:
        # ── Step 1: Sync Progress ────────────────────────────
        if not args.plan_only and not args.email_only:
            print("\n📡 Step 1: Syncing LeetCode progress...")
            sync_result = sync_leetcode_progress(db)
            print(f"   Result: {sync_result['status']}")
            if sync_result.get("synced"):
                print(f"   Matched: {sync_result['synced']} SDE sheet problems")

            if args.sync_only:
                print("\n✅ Sync complete. Exiting (--sync-only mode)")
                return

        # ── Step 2: Generate Daily Plan ──────────────────────
        if not args.email_only:
            print("\n📋 Step 2: Generating daily plan...")
            plan = generate_daily_plan(db)
            summary = get_plan_summary(plan)

            print(f"   Generated {summary['total_problems']} problems")
            print(f"   Estimated time: {summary['total_time_minutes']} minutes\n")

            for p in summary["problems"]:
                print(f"   {p['number']}. {p['badge']} {p['title']} ({p['difficulty']})")
                print(f"      Topic: {p['topic']} | Category: {p['category']}")
                print(f"      🔗 {p['url']}")
                print()
        else:
            # Load existing plan for email
            from app.database import get_schedule_for_date
            schedule = get_schedule_for_date(db, date.today())
            if not schedule:
                print("⚠️  No plan found for today. Generate one first.")
                return
            plan = [
                {"problem": e.problem, "category": e.category, "expected_time": e.expected_time}
                for e in schedule
            ]
            summary = get_plan_summary(plan)

        # ── Step 3: Send Email ───────────────────────────────
        if not args.no_email and not args.plan_only:
            print("📧 Step 3: Sending daily email...")
            email_result = send_daily_email(summary)
            print(f"   Result: {email_result['status']}")
            if email_result.get("message"):
                print(f"   {email_result['message']}")
        elif args.no_email:
            print("\n📧 Step 3: Skipped (--no-email flag)")

        print("\n" + "=" * 60)
        print("✅ Daily run complete!")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()
