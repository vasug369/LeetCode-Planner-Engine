"""Quick test script to verify data seeding and planner."""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["PYTHONIOENCODING"] = "utf-8"

from app.database import init_db, get_db, get_problem_count, get_topic_stats
from app.scraper import load_sde_sheet, get_sheet_stats

# Initialize
init_db()
load_sde_sheet()

# Verify
db = get_db()
count = get_problem_count(db)
stats = get_sheet_stats()
topics = get_topic_stats(db)

print(f"\n=== Data Seeding Test ===")
print(f"Problems in DB: {count}")
print(f"Problems in JSON: {stats['total_problems']}")
print(f"Topics: {stats['topic_count']}")
print(f"Difficulties: {stats['difficulties']}")
print(f"\n=== Topic Breakdown ===")
for t in topics:
    print(f"  {t['topic']}: {t['total']} problems")

# Test planner
from app.planner import generate_daily_plan, get_plan_summary
plan = generate_daily_plan(db)
summary = get_plan_summary(plan)
print(f"\n=== Planner Test ===")
print(f"Generated {summary['total_problems']} problems")
print(f"Estimated time: {summary['total_time_minutes']} minutes")
for p in summary["problems"]:
    print(f"  {p['number']}. [{p['difficulty']}] {p['title']} - {p['category']}")

db.close()
print("\nAll tests passed!")
