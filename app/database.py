"""Database initialization and CRUD utilities."""

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, date, timedelta
from typing import Optional

from app.config import settings
from app.models import Base, Problem, UserProgress, ScheduleEntry, DailyStreak

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get a database session."""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


# ── Problem CRUD ──────────────────────────────────────────────

def get_all_problems(db: Session) -> list[Problem]:
    return db.query(Problem).all()


def get_problem_by_slug(db: Session, slug: str) -> Optional[Problem]:
    return db.query(Problem).filter(Problem.slug == slug).first()


def get_problems_by_topic(db: Session, topic: str) -> list[Problem]:
    return db.query(Problem).filter(Problem.topic == topic).all()


def get_problems_by_difficulty(db: Session, difficulty: str) -> list[Problem]:
    return db.query(Problem).filter(Problem.difficulty == difficulty).all()


def get_all_topics(db: Session) -> list[str]:
    topics = db.query(Problem.topic).distinct().all()
    return [t[0] for t in topics]


def get_problem_count(db: Session) -> int:
    return db.query(Problem).count()


# ── UserProgress CRUD ────────────────────────────────────────

def get_unsolved_problems(db: Session) -> list[Problem]:
    """Get problems that haven't been solved yet."""
    solved_ids = db.query(UserProgress.problem_id).filter(UserProgress.solved == True).subquery()
    return db.query(Problem).filter(~Problem.id.in_(solved_ids)).all()


def get_solved_problems(db: Session) -> list[Problem]:
    """Get problems that are solved."""
    solved_ids = db.query(UserProgress.problem_id).filter(UserProgress.solved == True).subquery()
    return db.query(Problem).filter(Problem.id.in_(solved_ids)).all()


def get_solved_count(db: Session) -> int:
    return db.query(UserProgress).filter(UserProgress.solved == True).count()


def get_progress_for_problem(db: Session, problem_id: int) -> Optional[UserProgress]:
    return db.query(UserProgress).filter(UserProgress.problem_id == problem_id).first()


def upsert_progress(db: Session, problem_id: int, solved: bool, attempts: int = 1,
                     time_taken: float = None, last_submission_time: datetime = None):
    """Insert or update user progress for a problem."""
    progress = get_progress_for_problem(db, problem_id)
    if progress:
        progress.solved = solved
        progress.attempts = attempts
        if time_taken is not None:
            progress.time_taken = time_taken
        if last_submission_time is not None:
            progress.last_submission_time = last_submission_time
    else:
        progress = UserProgress(
            problem_id=problem_id,
            solved=solved,
            attempts=attempts,
            time_taken=time_taken,
            last_submission_time=last_submission_time,
        )
        db.add(progress)
    db.commit()
    return progress


# ── Topic Stats ──────────────────────────────────────────────

def get_topic_stats(db: Session) -> list[dict]:
    """Get completion stats per topic."""
    topics = get_all_topics(db)
    stats = []
    for topic in topics:
        total = db.query(Problem).filter(Problem.topic == topic).count()
        solved = (
            db.query(Problem)
            .join(UserProgress, Problem.id == UserProgress.problem_id)
            .filter(Problem.topic == topic, UserProgress.solved == True)
            .count()
        )
        avg_time = (
            db.query(func.avg(UserProgress.time_taken))
            .join(Problem, Problem.id == UserProgress.problem_id)
            .filter(Problem.topic == topic, UserProgress.time_taken.isnot(None))
            .scalar()
        )
        stats.append({
            "topic": topic,
            "total": total,
            "solved": solved,
            "completion_pct": round((solved / total) * 100, 1) if total > 0 else 0,
            "avg_time": round(avg_time, 1) if avg_time else None,
        })
    return stats


def get_weak_topics(db: Session, threshold_pct: float = 50.0) -> list[str]:
    """Get topics with completion below threshold."""
    stats = get_topic_stats(db)
    return [s["topic"] for s in stats if s["completion_pct"] < threshold_pct]


# ── Revision Candidates ─────────────────────────────────────

def get_revision_candidates(db: Session, days_since: int = 7) -> list[Problem]:
    """Get solved problems eligible for spaced repetition review."""
    cutoff = datetime.now() - timedelta(days=days_since)
    return (
        db.query(Problem)
        .join(UserProgress, Problem.id == UserProgress.problem_id)
        .filter(
            UserProgress.solved == True,
            UserProgress.last_submission_time < cutoff,
        )
        .all()
    )


# ── Schedule CRUD ────────────────────────────────────────────

def get_schedule_for_date(db: Session, target_date: date) -> list[ScheduleEntry]:
    return db.query(ScheduleEntry).filter(ScheduleEntry.date == target_date).all()


def create_schedule_entry(db: Session, target_date: date, problem_id: int,
                          category: str, expected_time: float = None) -> ScheduleEntry:
    entry = ScheduleEntry(
        date=target_date,
        problem_id=problem_id,
        category=category,
        expected_time=expected_time,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def mark_schedule_complete(db: Session, entry_id: int, status: str = "completed"):
    entry = db.query(ScheduleEntry).filter(ScheduleEntry.id == entry_id).first()
    if entry:
        entry.completion_status = status
        db.commit()
    return entry


def clear_schedule_for_date(db: Session, target_date: date):
    db.query(ScheduleEntry).filter(ScheduleEntry.date == target_date).delete()
    db.commit()


# ── Streak Tracking ──────────────────────────────────────────

def update_streak(db: Session, target_date: date, problems_done: int):
    streak = db.query(DailyStreak).filter(DailyStreak.date == target_date).first()
    if streak:
        streak.problems_completed = problems_done
        streak.streak_maintained = problems_done > 0
    else:
        streak = DailyStreak(
            date=target_date,
            problems_completed=problems_done,
            streak_maintained=problems_done > 0,
        )
        db.add(streak)
    db.commit()
    return streak


def get_current_streak(db: Session) -> int:
    """Calculate current consecutive day streak."""
    streaks = (
        db.query(DailyStreak)
        .filter(DailyStreak.streak_maintained == True)
        .order_by(DailyStreak.date.desc())
        .all()
    )
    if not streaks:
        return 0
    count = 0
    expected = date.today()
    for s in streaks:
        if s.date == expected or s.date == expected - timedelta(days=1):
            count += 1
            expected = s.date - timedelta(days=1)
        else:
            break
    return count


def get_longest_streak(db: Session) -> int:
    """Calculate longest ever streak."""
    streaks = (
        db.query(DailyStreak)
        .filter(DailyStreak.streak_maintained == True)
        .order_by(DailyStreak.date.asc())
        .all()
    )
    if not streaks:
        return 0
    longest = 1
    current = 1
    for i in range(1, len(streaks)):
        if (streaks[i].date - streaks[i - 1].date).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest
