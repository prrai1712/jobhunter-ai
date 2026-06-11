# JobHunter AI

A complete, production-grade, fully automated AI-powered job discovery and application platform. Controlled entirely via a secure Telegram Bot interface. Designed to run 24/7 on lightweight cloud hosting (such as Oracle Cloud Free Tier).

---

## Key Features

1. **Continuous Job Discovery**: Auto-crawls Greenhouse, Lever, and Ashby job boards of target companies.
2. **Salary Intelligence**: Aggregates and estimates compensation data by web scraping Glassdoor, Levels.fyi, and AmbitionBox.
3. **Advanced AI Matcher**: Semantically matches candidate resumes and profiles against job descriptions using custom natural language processing (NLP) and Jaccard similarity.
4. **Auto-Application Pipeline**: Submits job applications programmatically using the official ATS API interfaces. If custom/dynamic questions exist, falls back to automated headless Playwright browser filling (fully equipped with anti-detection bypasses).
5. **Secure Command Center**: A rich Telegram Bot interface with 23 commands for systems management, resume upload, live stats tables, company analytics, and data exports.

---

## Directory Layout

```
├── alembic/                  # Database schema migrations
├── data/                     # Persistent files (resumes, backups, reports)
├── docs/                     # Deployment & Maintenance guides
├── scripts/                  # Shell scripts for setup/deploy/backup/restore
├── src/
│   ├── appliers/             # Auto-apply engine & Playwright controller
│   ├── core/
│   │   ├── config/           # Pydantic Settings & Candidate configuration
│   │   ├── database/         # Async PostgreSQL session lifecycle
│   │   ├── models/           # SQLAlchemy models (25 tables)
│   │   ├── repositories/     # Data Access Layer (DAL) implementation
│   │   └── services/         # Application Business Logic
│   ├── logging/              # Structured JSON logging config
│   ├── matching/             # Skill extraction & Match scoring engine
│   ├── providers/            # Greenhouse, Lever, and Ashby parsers
│   ├── salary/               # Levels.fyi, Glassdoor, AmbitionBox scrapers
│   ├── scheduler/            # APScheduler automated cron routines
│   ├── storage/              # Disk files storage manager
│   ├── telegram/             # Bot setup, middleware, handlers & push alerts
│   └── main.py               # Main orchestrator entry point
├── pyproject.toml            # Project dependency definitions
└── docker-compose.yml        # Multi-container local/cloud deployment
```

---

## Core Technologies

- **Core Framework**: Python 3.12+ (Asyncio-driven)
- **Database**: PostgreSQL 16
- **Database Layer**: SQLAlchemy 2.0 (Asyncpg driver for app, Psycopg2-binary for APScheduler JobStore)
- **Migrations**: Alembic
- **Automation**: Playwright (Headless Chromium)
- **Parsing/Scraping**: BeautifulSoup4 + Lxml + HTTPX
- **NLP / Matching**: Custom Scikit-Learn Vectorizers & TF-IDF
- **Task Orchestration**: APScheduler (AsyncIOScheduler)
- **Interface**: python-telegram-bot v21+
- **Logging**: Structlog (JSON structure)
- **Containerization**: Docker & Docker Compose

---

## Quickstart Guide

### 1. Prerequisites
- Docker & Docker Compose
- A Telegram Bot token (generate one via [@BotFather](https://t.me/BotFather))
- Your Telegram user ID (use [@userinfobot](https://t.me/userinfobot) to find it)

### 2. Configure Environment
Clone the repository and copy the environment template:
```bash
cp .env.example .env
```
Edit the `.env` file and set the required variables:
- `TELEGRAM_BOT_TOKEN`: The token you received from BotFather.
- `ALLOWED_TELEGRAM_USER_ID`: Your Telegram User ID (keeps the bot private to you).
- `CANDIDATE_NAME`, `CANDIDATE_EMAIL`, `CANDIDATE_PHONE`, etc.
- Set up target Greenhouse board tokens, Lever companies, and Ashby boards.

### 3. Deploy
Launch the full container stack (database, backups, and app core):
```bash
./scripts/deploy.sh
```

### 4. Interactive Usage
Open Telegram, search for your bot, and send `/start`.
- Upload your resume PDF file directly.
- Send `/start_system` to enable automated schedules.
- Run `/system_status` to ensure healthy heartbeat logs.

---

## Telegram Commands List

| Category | Command | Purpose |
|---|---|---|
| **System** | `/start` | Welcome and help overview |
| | `/start_system` | Transition to RUNNING state, starts scheduler |
| | `/stop_system` | Transition to STOPPED state, pauses scheduler |
| | `/pause_applications` | Pauses application sending (keeps discovery active) |
| | `/resume_applications` | Resumes application sending |
| | `/help` | Explains all bot commands |
| **Resume** | `/upload_resume` | Prompts to upload a new resume PDF |
| | `/active_resume` | Displays details of the current active resume |
| | `/list_resumes` | Lists all uploaded resumes |
| | `/delete_resume <id>` | Soft-deletes a resume |
| **Jobs** | `/jobs_today` | Shows numbers of jobs scraped, matched, rejected |
| | `/job_details <id>` | Full description, salary estimate, match details |
| | `/approved_jobs` | Lists jobs that passed decision criteria |
| | `/rejected_jobs` | Lists rejected jobs and why |
| **Applications**| `/applications_today` | Summary of today's applications |
| | `/application_stats` | Success rates, average match scores, average salary |
| | `/application_history`| Paginated list of all applications |
| **Analytics** | `/company_stats` | Summarizes company discovery, applications, salaries |
| | `/salary_stats` | High/low/average salaries and histograms |
| | `/top_companies` | Top 10 companies by job postings found |
| **Admin** | `/system_status` | System health, worker heartbeats, DB status |
| | `/restart_workers` | Restart/re-registers APScheduler cron routines |
| | `/database_health` | Database connection pool stats, row counts |
| | `/export_report` | Generates a complete report file (CSV/Excel/PDF) |

---

## Documentation

For deep dives into configuration, setup, and recovery:
- See [Deployment Guide](docs/deployment.md) for step-by-step setup on Oracle Cloud VMs.
- See [Monitoring Guide](docs/monitoring.md) for logs parsing and performance tracking.
- See [Maintenance Guide](docs/maintenance.md) for database backups, restores, and extensions.

---

## License

This project is licensed under the MIT License.
