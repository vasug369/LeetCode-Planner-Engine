"""SMTP email service for sending daily problem plans."""

import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from jinja2 import Environment, FileSystemLoader
import os

from app.config import settings
from app.database import get_db, get_solved_count, get_problem_count, get_current_streak
import logging
import sys

logger = logging.getLogger("uvicorn")


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

MOTIVATIONAL_QUOTES = [
    "💪 Every problem you solve today brings you closer to your dream job!",
    "🔥 Consistency beats intensity. Keep showing up!",
    "🎯 You're building a skill that compounds. Trust the process!",
    "⚡ The best time to solve a problem was yesterday. The next best time is now!",
    "🌟 You're not just solving problems — you're becoming a problem solver.",
    "🚀 Small daily improvements lead to staggering long-term results.",
    "💎 Diamonds are made under pressure. Embrace the challenge!",
    "🏆 Every expert was once a beginner. Keep going!",
    "🧠 Your brain grows stronger with every problem. Feed it well!",
    "🎓 The SDE sheet is your roadmap. Follow it consistently and success will follow.",
]


def _render_email(plan_summary: dict, solved: int, total: int, streak: int) -> str:
    """Render the email HTML template with plan data."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("email_template.html")

    progress_pct = round((solved / total) * 100, 1) if total > 0 else 0

    # Pick a motivational message
    if progress_pct >= 80:
        motivation = "🏆 You're in the home stretch! Just a few more problems to finish the entire sheet. Incredible dedication!"
    elif progress_pct >= 50:
        motivation = f"🔥 Over halfway done! {solved} problems crushed. The momentum is unstoppable!"
    elif streak >= 7:
        motivation = f"🌟 {streak}-day streak! Your consistency is legendary. Keep it alive!"
    else:
        motivation = random.choice(MOTIVATIONAL_QUOTES)

    html = template.render(
        date=date.today().strftime("%A, %B %d, %Y"),
        solved=solved,
        total=total,
        progress_pct=progress_pct,
        total_time=int(plan_summary["total_time_minutes"]),
        total_problems=plan_summary["total_problems"],
        problems=plan_summary["problems"],
        motivation=motivation,
        streak=streak,
    )
    return html


def send_daily_email(plan_summary: dict) -> dict:
    """
    Send the daily problem plan via SMTP email.

    Args:
        plan_summary: Output from planner.get_plan_summary()

    Returns:
        dict with status and message.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return {"status": "error", "message": "SMTP credentials not configured in .env"}

    if not settings.EMAIL_TO:
        return {"status": "error", "message": "EMAIL_TO not configured in .env"}

    db = get_db()
    try:
        solved = get_solved_count(db)
        total = get_problem_count(db)
        streak = get_current_streak(db)

        # Render email HTML
        html_content = _render_email(plan_summary, solved, total, streak)

        # Build email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📚 Your LeetCode Plan — {date.today().strftime('%b %d')} | {plan_summary['total_problems']} Problems"
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.EMAIL_TO

        # Plain text fallback
        plain_text = f"Daily LeetCode Plan - {date.today()}\n\n"
        for p in plan_summary["problems"]:
            plain_text += f"{p['number']}. [{p['difficulty']}] {p['title']} — {p['topic']}\n"
            plain_text += f"   Link: {p['url']}\n"
            plain_text += f"   Expected: ~{p['expected_time']} min\n\n"
        plain_text += f"\nProgress: {solved}/{total} ({round((solved/total)*100, 1) if total else 0}%)\n"

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Send email
        logger.info(f"📧 Attempting to connect to SMTP {settings.SMTP_HOST}:{settings.SMTP_PORT}...")
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            logger.info("📡 Starting TLS...")
            server.starttls()
            server.ehlo()
            logger.info(f"🔑 Logging in as {settings.SMTP_USER}...")
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            logger.info("📤 Sending mail content...")
            server.sendmail(settings.SMTP_USER, settings.EMAIL_TO, msg.as_string())

        logger.info(f"✅ Email sent to {settings.EMAIL_TO}")
        return {"status": "success", "message": f"Email sent to {settings.EMAIL_TO}"}

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ SMTP authentication failed. Check your email/password in .env")
        return {"status": "error", "message": "SMTP authentication failed. Check your email/password in .env"}
    except Exception as e:
        logger.error(f"❌ Failed to send email: {str(e)}")
        return {"status": "error", "message": f"Failed to send email: {str(e)}"}
    finally:
        db.close()
        sys.stdout.flush()


if __name__ == "__main__":
    # Test email rendering
    test_summary = {
        "date": date.today().isoformat(),
        "total_problems": 4,
        "total_time_minutes": 105,
        "problems": [
            {"number": 1, "title": "Two Sum", "difficulty": "Easy", "badge": "🟢",
             "topic": "Arrays", "category": "Easy", "url": "https://leetcode.com/problems/two-sum/",
             "expected_time": 15},
            {"number": 2, "title": "Merge Intervals", "difficulty": "Medium", "badge": "🟡",
             "topic": "Arrays", "category": "Medium", "url": "https://leetcode.com/problems/merge-intervals/",
             "expected_time": 30},
            {"number": 3, "title": "LRU Cache", "difficulty": "Medium", "badge": "🟡",
             "topic": "Stack and Queue", "category": "Medium", "url": "https://leetcode.com/problems/lru-cache/",
             "expected_time": 35},
            {"number": 4, "title": "Binary Search", "difficulty": "Easy", "badge": "🟢",
             "topic": "Binary Search", "category": "Revision", "url": "https://leetcode.com/problems/binary-search/",
             "expected_time": 10},
        ],
    }

    html = _render_email(test_summary, 45, 191, 5)
    with open("test_email.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("📧 Test email rendered to test_email.html")
