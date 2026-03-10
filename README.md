# 🚀 LeetCode Planner Engine

A personal LeetCode preparation planner system that helps you complete the **Striver SDE Sheet** (~190 problems) in an optimal and systematic way.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square)

## ✨ Features

- **📡 LeetCode Sync** — Automatically syncs your LeetCode progress via GraphQL API
- **🧠 Smart Planner** — Generates daily plans with difficulty mixing, weak-topic targeting, and spaced repetition
- **📧 Email Automation** — Sends beautiful daily emails with your personalized problem list
- **📊 Dashboard** — Interactive dark-themed dashboard with progress charts, topic breakdown, and streak tracking
- **⏰ Auto Scheduling** — Run daily via cron/Task Scheduler for hands-free operation

## 🏗️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python + FastAPI |
| Database | SQLite + SQLAlchemy |
| API | LeetCode GraphQL |
| Email | SMTP + Jinja2 Templates |
| Dashboard | HTML/CSS/JS + Chart.js |
| Scheduling | Cron / Windows Task Scheduler |

## 📦 Installation

### 1. Clone & Setup

```bash
cd "LeetCode Planner Engine"

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
copy .env.example .env    # Windows
cp .env.example .env      # macOS/Linux
```

Edit `.env` with your settings:

```env
# Your LeetCode username (public profile)
LEETCODE_USERNAME=your_leetcode_username

# Gmail SMTP (use App Password, not regular password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_TO=recipient@gmail.com
```

#### Setting up Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** if not already enabled
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Generate a new app password for "Mail"
5. Use this 16-character password as `SMTP_PASSWORD` in `.env`

### 3. Initialize Database

The database is automatically created when you first run the server or daily runner.

## 🚀 Usage

### Start the Dashboard Server

```bash
python main.py
```

Then open **http://localhost:8000** in your browser.

### Dashboard Features

| Button | Action |
|--------|--------|
| 🔄 **Sync LeetCode** | Fetches your latest solved problems from LeetCode |
| 📋 **Generate Plan** | Creates today's 4-problem study plan |
| 📧 **Send Email** | Sends the daily plan to your configured email |

### Daily Runner (CLI)

```bash
# Full daily run: sync → plan → email
python daily_run.py

# Without email
python daily_run.py --no-email

# Sync LeetCode progress only
python daily_run.py --sync-only

# Generate plan only (no sync, no email)
python daily_run.py --plan-only

# Send email with existing plan
python daily_run.py --email-only
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard |
| `GET` | `/api/stats` | Overall progress stats |
| `GET` | `/api/topics` | Topic-wise breakdown |
| `GET` | `/api/schedule/today` | Today's schedule |
| `GET` | `/api/problems` | All SDE sheet problems |
| `POST` | `/api/sync` | Sync LeetCode progress |
| `POST` | `/api/generate-plan` | Generate daily plan |
| `POST` | `/api/send-email` | Send daily email |
| `POST` | `/api/schedule/{id}/complete` | Mark problem done |
| `POST` | `/api/schedule/{id}/skip` | Skip a problem |

## ☁️ Cloud Deployment (100% Free & Infinite)

Since free hosting services (like Render or Vercel) wipe local files and go to sleep after 15 minutes of inactivity, you cannot rely securely on local `.db` files or internal timers to run a 24/7 autonomous bot.

To make this completely cloud-native and truly infinite for free, follow these three steps:

### 1. Set Up a Cloud Database (Supabase)
Instead of a local SQLite file, we use a free cloud PostgreSQL database so your progress is never wiped.
1. Go to [Supabase](https://supabase.com/) and create a free project.
2. Go to **Project Settings** → **Database** and copy the **Connection string (URI)**.
3. It will look like: `postgresql://postgres.[project]:[password]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres`
4. Set this as your `DATABASE_URL`.

### 2. Deploy to Render
We have included a `render.yaml` file to make deployment 1-click easy.
1. Push this entire project to a private GitHub repository.
2. Go to [Render.com](https://render.com/) → **New** → **Blueprint**.
3. Connect your GitHub repository.
4. Render will automatically detect the settings. You will need to fill in your Environment Variables (like `LEETCODE_USERNAME`, `SMTP_PASSWORD`, and the `DATABASE_URL` from Supabase).
5. **Crucial:** Invent a secure password and put it in the `CRON_SECRET` variable.
6. Click **Apply**. When it finishes, copy your bolded Render URL (e.g., `https://leetcode-planner-xyz.onrender.com`).

### 3. Set Up External Cron Jobs
Instead of the app trying to keep itself awake, we use an external pinger to trigger the sync and email endpoints securely.
1. Go to [Cron-job.org](https://cron-job.org/) (Free).
2. Create **Job 1 (Auto-Sync)**:
   - **URL**: `https://[YOUR_RENDER_URL]/api/cron/sync`
   - **Schedule**: Every 30 minutes.
   - **Headers**: Add `Authorization: Bearer YOUR_CRON_SECRET`
3. Create **Job 2 (Daily Planner & Email)**:
   - **URL**: `https://[YOUR_RENDER_URL]/api/cron/daily`
   - **Schedule**: Daily at 07:00 AM (choose your timezone).
   - **Headers**: Add `Authorization: Bearer YOUR_CRON_SECRET`

**That's it!** Your app is now an immortal cloud service. The external cron jobs will automatically wake up your Render server and execute your tasks securely.

---

### Using Local CLI (Optional)
If you prefer not to keep the server running 24/7, you can use cron or Windows Task Scheduler with the `daily_run.py` script:

#### Windows Task Scheduler
1. Create Basic Task: `LeetCode Daily Planner`
2. Trigger: Daily at 7:00 AM
3. Action: Start a program (`path\to\venv\Scripts\python.exe` with arguments `daily_run.py`)

#### Linux/macOS Cron
```bash
0 7 * * * cd /path/to/LeetCode\ Planner\ Engine && /path/to/venv/bin/python daily_run.py
```

## 🧠 Planning Algorithm

The smart planner generates **4 problems per day**:

| Slot | Difficulty | Selection Strategy |
|------|-----------|-------------------|
| 1 | Easy | From least-covered topic |
| 2 | Medium | From weak topics (high avg time / low completion) |
| 3 | Medium | From weak topics |
| 4 | Revision / Weak | Spaced repetition (>7 days since solve) or weak-topic problem |

**Adaptive features:**
- Topics with low completion or high solve times get increased frequency
- Solved problems resurface for revision via spaced repetition
- Topic balancing ensures broad coverage across all 28 topics

## 📁 Project Structure

```
LeetCode Planner Engine/
├── app/
│   ├── config.py              # Environment settings
│   ├── models.py              # SQLAlchemy ORM models
│   ├── database.py            # DB setup + CRUD operations
│   ├── scraper.py             # SDE sheet data loader
│   ├── leetcode_client.py     # LeetCode GraphQL API client
│   ├── planner.py             # Smart planning algorithm
│   ├── scheduler.py           # Progress sync module
│   ├── email_service.py       # SMTP email sender
│   ├── routes.py              # FastAPI API routes
│   └── templates/
│       ├── dashboard.html     # Interactive dashboard UI
│       └── email_template.html # Email HTML template
├── data/
│   └── sde_sheet_problems.json # SDE sheet problem data
├── main.py                     # FastAPI server entry point
├── daily_run.py                # Standalone daily runner
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|---------|
| `LEETCODE_USERNAME not set` | Add your username to `.env` |
| `SMTP authentication failed` | Use a Gmail App Password, not your regular password |
| `No problems found` | Run the server first to auto-seed the database |
| `API rate limited` | LeetCode may throttle requests; wait a few minutes |

## 📄 License

This project is for personal educational use. Problem data references the [Striver SDE Sheet](https://takeuforward.org/dsa/strivers-sde-sheet-top-coding-interview-problems) by [takeUforward](https://takeuforward.org).
