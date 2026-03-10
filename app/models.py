"""SQLAlchemy ORM models for the LeetCode Planner Engine."""

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, Date,
    ForeignKey, Text, create_engine
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Problem(Base):
    """Striver SDE Sheet problem."""

    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    topic = Column(String(100), nullable=False)
    difficulty = Column(String(20), nullable=False)  # Easy, Medium, Hard
    leetcode_url = Column(String(500), nullable=False)

    # Relationships
    progress = relationship("UserProgress", back_populates="problem", uselist=False)
    schedules = relationship("ScheduleEntry", back_populates="problem")

    def __repr__(self):
        return f"<Problem(id={self.id}, title='{self.title}', topic='{self.topic}')>"


class UserProgress(Base):
    """User's progress on a specific problem."""

    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), unique=True, nullable=False)
    solved = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    time_taken = Column(Float, nullable=True)  # minutes
    last_submission_time = Column(DateTime, nullable=True)
    accuracy = Column(Float, nullable=True)  # percentage 0-100

    # Relationships
    problem = relationship("Problem", back_populates="progress")

    def __repr__(self):
        return f"<UserProgress(problem_id={self.problem_id}, solved={self.solved})>"


class ScheduleEntry(Base):
    """Daily schedule entry linking a date to an assigned problem."""

    __tablename__ = "schedule_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    category = Column(String(50), nullable=False)  # easy, medium, revision, weak_topic
    completion_status = Column(String(20), default="pending")  # pending, completed, skipped
    expected_time = Column(Float, nullable=True)  # estimated minutes

    # Relationships
    problem = relationship("Problem", back_populates="schedules")

    def __repr__(self):
        return f"<ScheduleEntry(date={self.date}, problem_id={self.problem_id}, status={self.completion_status})>"


class DailyStreak(Base):
    """Track daily completion streaks."""

    __tablename__ = "daily_streaks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False)
    problems_completed = Column(Integer, default=0)
    streak_maintained = Column(Boolean, default=False)
