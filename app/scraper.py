"""Load Striver SDE sheet data from JSON file and seed the database."""

import json
import os
from sqlalchemy.orm import Session

from app.models import Problem
from app.database import get_db, init_db


DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sde_sheet_problems.json")


def load_sde_sheet(db: Session = None) -> int:
    """
    Load all SDE sheet problems from JSON into the database.
    Returns the number of problems inserted.
    """
    close_db = False
    if db is None:
        db = get_db()
        close_db = True

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            problems = json.load(f)

        inserted = 0
        seen_slugs = set()
        for p in problems:
            slug = p["slug"]
            # Skip duplicates within the same batch
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            existing = db.query(Problem).filter(Problem.slug == slug).first()
            if not existing:
                problem = Problem(
                    title=p["title"],
                    slug=slug,
                    topic=p["topic"],
                    difficulty=p["difficulty"],
                    leetcode_url=p["leetcode_url"],
                )
                db.add(problem)
                db.flush()
                inserted += 1

        db.commit()
        print(f"✅ Loaded {inserted} new problems ({len(problems)} total in sheet)")
        return inserted

    finally:
        if close_db:
            db.close()


def get_sheet_stats() -> dict:
    """Get basic stats about the SDE sheet data."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        problems = json.load(f)

    topics = {}
    difficulties = {"Easy": 0, "Medium": 0, "Hard": 0}

    for p in problems:
        topic = p["topic"]
        topics[topic] = topics.get(topic, 0) + 1
        difficulties[p["difficulty"]] = difficulties.get(p["difficulty"], 0) + 1

    return {
        "total_problems": len(problems),
        "topics": topics,
        "difficulties": difficulties,
        "topic_count": len(topics),
    }


if __name__ == "__main__":
    init_db()
    load_sde_sheet()
    stats = get_sheet_stats()
    print(f"\n📊 SDE Sheet Stats:")
    print(f"   Total Problems: {stats['total_problems']}")
    print(f"   Topics: {stats['topic_count']}")
    print(f"   Easy: {stats['difficulties']['Easy']}, Medium: {stats['difficulties']['Medium']}, Hard: {stats['difficulties']['Hard']}")
