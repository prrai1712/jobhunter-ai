# Monitoring Guide

This document describes how to monitor, debug, and troubleshoot **JobHunter AI** during production operations.

---

## 1. Structured Logging System

JobHunter AI uses `structlog` for structured logging. Logs are formatted in JSON in production and as colorized text in development environments.

Every log entry includes key fields:
- `timestamp`: UTC ISO 8601 timestamp.
- `level`: Log level (`info`, `warning`, `error`, `debug`).
- `event`: Machine-parseable event name (e.g., `job_discovered`, `apply_attempt_failed`).
- `logger`: Subsystem module.
- `metadata`: Key-value properties representing context (e.g., `job_id`, `application_id`, `company_name`, `error_message`).

---

## 2. Docker Logs Parsing

Use docker logging tools to monitor system activities.

### View all logs in real-time:
```bash
docker compose logs -f app
```

### Search logs for specific errors:
```bash
docker compose logs app | grep -i "error"
```

### Trace a specific job or application pipeline:
Each job discovery run or application has a unique ID associated with it. You can isolate trace messages by grepping its ID:
```bash
docker compose logs app | grep "job_id='d3b07384d113'"
```

---

## 3. Investigating Application Failures

If an application fails during form filling, the system logs the failure details and saves troubleshooting assets.

### Step 1: Query the Failed Job via Telegram
Send `/rejected_jobs` or `/application_history` to the bot to get the unique Application ID or Job ID. You can also run `/job_details <id>` to see the exact rejection reason or failure message.

### Step 2: Locate Screenshots & HTML Snapshots
Inside the container's volume (or local `./data` folder), browse the logs directories:
- **Screenshots**: `./data/screenshots/{date}/`
- **HTML Code Snapshots**: `./data/html_snapshots/{date}/`

Files are named in the format:
- Screenshot: `{job_id}_{step_name}_{time}.png`
- HTML: `{job_id}_{time}.html`

Download these assets to your local device to visually inspect why the browser failed (e.g., bot detection captcha, modified input fields, missing file inputs).

---

## 4. Bot Health Check & System Status

You can monitor database pools, scheduler triggers, and active workers directly from Telegram:

- **/system_status**:
  Displays global state, scheduler job triggers, active system settings, disk space, and worker heartbeats.
- **/database_health**:
  Queries PostgreSQL status:
  - Active connection counts
  - Pool sizes
  - Record counts across key tables (`jobs`, `applications`, `resumes`)
  - Disk usage of tables
- **/restart_workers**:
  Triggers a soft restart of the APScheduler job loop without stopping the main process container. Use this if a scraper or scheduler runner becomes unresponsive or hangs.
