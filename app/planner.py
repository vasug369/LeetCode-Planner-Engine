"""
Smart planning algorithm for daily problem scheduling.

Generates a daily schedule of 4 problems:
- 1 Easy (from least-covered topic)
- 2 Medium (prioritizing weak topics)
- 1 Revision or Weak-topic problem (spaced repetition)
"""

import random
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Problem, UserProgress, ScheduleEntry
from app.database import (
    get_db, get_unsolved_problems, get_solved_problems,
    get_topic_stats, get_weak_topics, get_revision_candidates,
    get_schedule_for_date, create_schedule_entry, clear_schedule_for_date,
    get_problems_by_topic, get_all_topics,
)


# ── Default time estimates by difficulty (minutes) ───────────

DEFAULT_TIME_ESTIMATES = {
    "Easy": 15,
    "Medium": 30,
    "Hard": 50,
}


def _get_estimated_time(problem: Problem, db: Session) -> float:
    """Estimate solve time based on user's history or defaults."""
    progress = (
        db.query(UserProgress)
        .filter(UserProgress.problem_id == problem.id)
        .first()
    )
    if progress and progress.time_taken:
        return progress.time_taken

    # Use average time for this difficulty from user's history
    avg_time = (
        db.query(func.avg(UserProgress.time_taken))
        .join(Problem, Problem.id == UserProgress.problem_id)
        .filter(
            Problem.difficulty == problem.difficulty,
            UserProgress.time_taken.isnot(None),
        )
        .scalar()
    )
    if avg_time:
        return round(avg_time, 1)

    return DEFAULT_TIME_ESTIMATES.get(problem.difficulty, 30)


def _get_topic_priority(db: Session) -> list[dict]:
    """
    Get topics sorted by priority (lowest completion first).
    Topics with high avg solve time get extra priority boost.
    """
    stats = get_topic_stats(db)

    # Calculate global avg time
    all_times = [s["avg_time"] for s in stats if s["avg_time"] is not None]
    global_avg = sum(all_times) / len(all_times) if all_times else 30

    for s in stats:
        # Base priority: inverse of completion percentage
        priority = 100 - s["completion_pct"]

        # Boost priority if avg time is above global average (struggling topic)
        if s["avg_time"] and s["avg_time"] > global_avg * 1.2:
            priority += 20

        # Boost priority if very few solved
        if s["completion_pct"] < 25:
            priority += 15

        s["priority"] = priority

    stats.sort(key=lambda x: x["priority"], reverse=True)
    return stats


def _pick_unsolved_by_difficulty(db: Session, difficulty: str,
                                  preferred_topics: list[str] = None,
                                  exclude_ids: set = None) -> Optional[Problem]:
    """Pick an unsolved problem of given difficulty, preferring certain topics."""
    exclude_ids = exclude_ids or set()

    unsolved = get_unsolved_problems(db)
    candidates = [
        p for p in unsolved
        if p.difficulty == difficulty and p.id not in exclude_ids
    ]

    if not candidates:
        # Fallback: try any unsolved problem
        candidates = [p for p in unsolved if p.id not in exclude_ids]
        if not candidates:
            return None

    # Try to pick from preferred topics first
    if preferred_topics:
        for topic in preferred_topics:
            topic_matches = [p for p in candidates if p.topic == topic]
            if topic_matches:
                return random.choice(topic_matches)

    return random.choice(candidates) if candidates else None


def _pick_revision_problem(db: Session, exclude_ids: set = None) -> Optional[Problem]:
    """Pick a solved problem for spaced repetition review."""
    exclude_ids = exclude_ids or set()

    # Priority 1: Problems solved >14 days ago (need revision most)
    old_candidates = get_revision_candidates(db, days_since=14)
    old_candidates = [p for p in old_candidates if p.id not in exclude_ids]
    if old_candidates:
        return random.choice(old_candidates)

    # Priority 2: Problems solved >7 days ago
    recent_candidates = get_revision_candidates(db, days_since=7)
    recent_candidates = [p for p in recent_candidates if p.id not in exclude_ids]
    if recent_candidates:
        return random.choice(recent_candidates)

    return None


def generate_daily_plan(db: Session = None, target_date: date = None) -> list[dict]:
    """
    Generate a daily study plan with 4 problems.

    Returns list of dicts:
    [
        {"problem": Problem, "category": str, "expected_time": float},
        ...
    ]
    """
    close_db = False
    if db is None:
        db = get_db()
        close_db = True

    if target_date is None:
        target_date = date.today()

    try:
        # Check if schedule already exists for this date
        existing = get_schedule_for_date(db, target_date)
        if existing:
            return [
                {
                    "problem": entry.problem,
                    "category": entry.category,
                    "expected_time": entry.expected_time,
                    "entry_id": entry.id,
                    "status": entry.completion_status,
                }
                for entry in existing
            ]

        # Get topic priorities
        topic_priorities = _get_topic_priority(db)
        weak_topics = [t["topic"] for t in topic_priorities[:5]]
        all_topic_names = [t["topic"] for t in topic_priorities]

        plan = []
        used_ids = set()

        # ── 1. Pick 1 Easy problem ─────────────────────────────
        easy = _pick_unsolved_by_difficulty(db, "Easy", all_topic_names, used_ids)
        if easy:
            plan.append({
                "problem": easy,
                "category": "easy",
                "expected_time": _get_estimated_time(easy, db),
            })
            used_ids.add(easy.id)

        # ── 2. Pick 2 Medium problems (prioritize weak topics) ─
        for _ in range(2):
            medium = _pick_unsolved_by_difficulty(db, "Medium", weak_topics, used_ids)
            if medium:
                plan.append({
                    "problem": medium,
                    "category": "medium",
                    "expected_time": _get_estimated_time(medium, db),
                })
                used_ids.add(medium.id)

        # ── 3. Pick 1 Revision or Weak-topic problem ──────────
        revision = _pick_revision_problem(db, used_ids)
        if revision:
            plan.append({
                "problem": revision,
                "category": "revision",
                "expected_time": _get_estimated_time(revision, db),
            })
            used_ids.add(revision.id)
        else:
            # No revision candidates: pick a weak-topic unsolved problem
            weak = _pick_unsolved_by_difficulty(db, "Medium", weak_topics, used_ids)
            if not weak:
                weak = _pick_unsolved_by_difficulty(db, "Hard", weak_topics, used_ids)
            if weak:
                plan.append({
                    "problem": weak,
                    "category": "weak_topic",
                    "expected_time": _get_estimated_time(weak, db),
                })
                used_ids.add(weak.id)

        # Save schedule to database
        for item in plan:
            entry = create_schedule_entry(
                db, target_date, item["problem"].id,
                item["category"], item["expected_time"]
            )
            item["entry_id"] = entry.id
            item["status"] = "pending"

        return plan

    finally:
        if close_db:
            db.close()


def get_plan_summary(plan: list[dict]) -> dict:
    """Generate a human-readable summary of the daily plan."""
    total_time = sum(item["expected_time"] for item in plan)
    problems_text = []

    for i, item in enumerate(plan, 1):
        p = item["problem"]
        badge = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}.get(p.difficulty, "⚪")
        category_label = item["category"].replace("_", " ").title()
        problems_text.append({
            "number": i,
            "title": p.title,
            "difficulty": p.difficulty,
            "badge": badge,
            "topic": p.topic,
            "category": category_label,
            "url": p.leetcode_url,
            "expected_time": item["expected_time"],
        })

    return {
        "date": date.today().isoformat(),
        "total_problems": len(plan),
        "total_time_minutes": round(total_time, 0),
        "problems": problems_text,
    }


if __name__ == "__main__":
    from app.database import init_db
    from app.scraper import load_sde_sheet

    init_db()
    load_sde_sheet()

    plan = generate_daily_plan()
    summary = get_plan_summary(plan)

    print(f"\n📅 Daily Plan for {summary['date']}")
    print(f"   Total problems: {summary['total_problems']}")
    print(f"   Estimated time: {summary['total_time_minutes']} minutes\n")

    for p in summary["problems"]:
        print(f"   {p['number']}. {p['badge']} {p['title']} ({p['difficulty']}) — {p['topic']}")
        print(f"      Category: {p['category']} | ⏱ ~{p['expected_time']}min")
        print(f"      🔗 {p['url']}\n")
