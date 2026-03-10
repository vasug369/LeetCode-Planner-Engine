"""Progress sync module — syncs LeetCode data into local database."""

from datetime import datetime
from sqlalchemy.orm import Session

from app.database import get_db, get_all_problems, upsert_progress, get_problem_by_slug
from app.leetcode_client import get_recent_submissions, get_user_solved_problems
from app.config import settings


def sync_leetcode_progress(db: Session = None, username: str = None) -> dict:
    """
    Sync the user's LeetCode progress into the local database.

    1. Fetches recent accepted submissions from LeetCode API
    2. Matches them against SDE sheet problems
    3. Updates the user_progress table

    Returns a summary of the sync operation.
    """
    close_db = False
    if db is None:
        db = get_db()
        close_db = True

    username = username or settings.LEETCODE_USERNAME

    try:
        if not username:
            return {"status": "error", "message": "No LeetCode username configured"}

        print(f"🔄 Syncing LeetCode progress for: {username}")

        # Fetch solved problem slugs
        solved_slugs = get_user_solved_problems(username)
        if not solved_slugs:
            return {"status": "warning", "message": "No solved problems found or API error"}

        # Fetch recent submissions for timestamp data
        submissions = get_recent_submissions(username, limit=500)
        submission_map = {}
        for sub in submissions:
            slug = sub["slug"]
            if slug not in submission_map:
                submission_map[slug] = sub

        # Match against SDE sheet problems
        all_problems = get_all_problems(db)
        problem_slug_map = {p.slug: p for p in all_problems}

        synced = 0
        matched = 0

        for slug in solved_slugs:
            if slug in problem_slug_map:
                matched += 1
                problem = problem_slug_map[slug]
                sub_data = submission_map.get(slug, {})

                upsert_progress(
                    db=db,
                    problem_id=problem.id,
                    solved=True,
                    attempts=1,  # API doesn't easily provide attempt count
                    time_taken=None,  # Can't reliably determine from API
                    last_submission_time=sub_data.get("timestamp"),
                )
                synced += 1

        result = {
            "status": "success",
            "username": username,
            "total_solved_on_leetcode": len(solved_slugs),
            "matched_to_sde_sheet": matched,
            "synced": synced,
            "timestamp": datetime.now().isoformat(),
        }

        print(f"✅ Sync complete: {synced} SDE sheet problems matched out of {len(solved_slugs)} total solved")
        return result

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    from app.database import init_db
    from app.scraper import load_sde_sheet

    init_db()
    load_sde_sheet()

    result = sync_leetcode_progress()
    print(f"\n📊 Sync Result: {result}")
