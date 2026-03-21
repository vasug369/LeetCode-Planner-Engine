"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration for the LeetCode Planner Engine."""

    # LeetCode
    LEETCODE_USERNAME: str = os.getenv("LEETCODE_USERNAME", "")
    LEETCODE_GRAPHQL_URL: str = "https://leetcode.com/graphql"

    # SMTP Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_TO: str = os.getenv("EMAIL_TO", "")

    # Planner
    DAILY_PROBLEMS: int = int(os.getenv("DAILY_PROBLEMS", "4"))
    AUTO_SYNC_INTERVAL_MINUTES: int = int(os.getenv("AUTO_SYNC_INTERVAL_MINUTES", "30"))
    DAILY_EMAIL_TIME: str = os.getenv("DAILY_EMAIL_TIME", "07:00")

    # Cloud Settings
    CRON_SECRET: str = os.getenv("CRON_SECRET", "change_me_in_production")

    # Resend Email (HTTP-based, works on Railway/platforms that block SMTP)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM: str = os.getenv("RESEND_FROM", "LeetCode Planner <onboarding@resend.dev>")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./leetcode_planner.db")


settings = Settings()
