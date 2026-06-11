# Maintenance & Customization Guide

This document describes standard database maintenance tasks, creating migrations, and extending the code structure to support new scraper providers.

---

## 1. Database Backups & Restores

Although the `jobhunter_backup` container automatically runs backups daily at 2 AM, you can manage backups manually.

### Run a Manual Backup
Execute the script from the root directory:
```bash
./scripts/backup.sh
```
This dumps the database to a file named `manual_backup_YYYYMMDD_HHMMSS.sql` inside `./data/backups/`. It keeps only the last 15 manual backups.

### Restore the Database
To restore the database from a previous SQL backup file (Warning: this overwrites the current database state):
```bash
./scripts/restore.sh ./data/backups/backup_20260611_020000.sql
```
This script terminates active connections, drops the old database, recreates it, streams the SQL commands, and restarts the application core.

---

## 2. Database Migrations (Alembic)

If you modify SQLAlchemy models in `src/core/models/`, you must update the database schema via migrations.

### Generate a Migration Script
```bash
# Run inside the app container
docker compose exec app alembic revision --autogenerate -m "describe_changes"
```
This creates a new Python migration file in `./alembic/versions/`.

### Review and Apply
Review the generated file to ensure it matches your changes, then run the upgrade command:
```bash
docker compose exec app alembic upgrade head
```

---

## 3. Adding a New ATS Provider

To support a new job board system (e.g., Workable):

### Step 1: Implement the Class
Create a new file `src/providers/workable.py` implementing `ATSProvider`:
```python
from src.providers.base import ATSProvider, DiscoveredJob, ApplicationResult

class WorkableProvider(ATSProvider):
    async def discover_jobs(self, board_token: str, **kwargs) -> list[DiscoveredJob]:
        # Scrape or fetch jobs from API
        pass

    async def apply_to_job(self, job_url: str, external_id: str, board_token: str, resume_path: str, candidate: dict) -> ApplicationResult:
        # Submit application (API request or Playwright browser)
        pass

    @property
    def provider_name(self) -> str:
        return "workable"
```

### Step 2: Register the Provider
Import and add your new provider inside `src/providers/registry.py`:
```diff
 from src.providers.greenhouse import GreenhouseProvider
 from src.providers.lever import LeverProvider
 from src.providers.ashby import AshbyProvider
+from src.providers.workable import WorkableProvider

 def register_all_providers() -> None:
     ProviderRegistry.register("greenhouse", GreenhouseProvider())
     ProviderRegistry.register("lever", LeverProvider())
     ProviderRegistry.register("ashby", AshbyProvider())
+    ProviderRegistry.register("workable", WorkableProvider())
```

---

## 4. Extending Salary intelligence

To add a new salary provider source (e.g., LinkedIn Salaries):

### Step 1: Implement the Class
Create a new file `src/salary/linkedin.py` implementing `SalaryProvider`:
```python
from src.salary.base import SalaryProvider, SalaryResult

class LinkedInSalaryProvider(SalaryProvider):
    async def estimate_salary(self, company: str, role: str, location: str) -> SalaryResult | None:
        # Scraping logic
        pass

    def provider_name(self) -> str:
        return "linkedin"

    def weight(self) -> float:
        return 0.25 # Adjust other weights accordingly in engine.py
```

### Step 2: Register in Salary Engine
Import and initialize the new provider inside `src/salary/engine.py`:
```diff
 from src.salary.levels import LevelsFyiProvider
 from src.salary.glassdoor import GlassdoorProvider
 from src.salary.ambitionbox import AmbitionBoxProvider
+from src.salary.linkedin import LinkedInSalaryProvider

 class SalaryEngine:
     def __init__(self):
         self.providers = [
             LevelsFyiProvider(),
             GlassdoorProvider(),
             AmbitionBoxProvider(),
+            LinkedInSalaryProvider(),
         ]
```

---

## 5. Cleaning Up Old Files

Screenshot files and HTML snapshots can take up disk space over time.
The daily scheduled job `cleanup_old_data` automatically archives files older than 30 days. You can adjust the cleanup window by updating the scheduler settings in `src/core/config/settings.py` or `.env`:
- `STORAGE_CLEANUP_DAYS`: Number of days to retain screenshots and reports.
