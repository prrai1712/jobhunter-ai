"""File storage management — structured directories for resumes, screenshots, reports."""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path

import structlog

from src.core.config.settings import get_settings

logger = structlog.get_logger(__name__)


class FileStorage:
    """Manages structured file storage directories."""

    def __init__(self) -> None:
        self.settings = get_settings().storage

    def ensure_directories(self) -> None:
        """Create all storage directories."""
        self.settings.ensure_dirs()
        logger.info("storage_directories_created")

    def save_resume(self, file_bytes: bytes, filename: str) -> Path:
        """Save a resume file."""
        self.settings.resume_dir.mkdir(parents=True, exist_ok=True)
        import uuid
        ext = Path(filename).suffix or ".pdf"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        filepath = self.settings.resume_dir / unique_name
        filepath.write_bytes(file_bytes)
        return filepath

    def save_screenshot(self, image_bytes: bytes, job_id: str, step: str) -> Path:
        """Save a screenshot with date-based organization."""
        date_dir = self.settings.screenshot_dir / datetime.now().strftime("%Y%m%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{job_id}_{step}_{datetime.now().strftime('%H%M%S')}.png"
        filepath = date_dir / filename
        filepath.write_bytes(image_bytes)
        return filepath

    def save_html_snapshot(self, html: str, job_id: str) -> Path:
        """Save an HTML snapshot with date-based organization."""
        date_dir = self.settings.html_snapshot_dir / datetime.now().strftime("%Y%m%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{job_id}_{datetime.now().strftime('%H%M%S')}.html"
        filepath = date_dir / filename
        filepath.write_text(html, encoding="utf-8")
        return filepath

    def save_export(self, file_bytes: bytes, filename: str) -> Path:
        """Save an export file."""
        self.settings.export_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.settings.export_dir / filename
        filepath.write_bytes(file_bytes)
        return filepath

    def cleanup_old_files(self, max_age_days: int = 30) -> int:
        """Remove files older than max_age_days from screenshots and snapshots."""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed = 0

        for directory in [self.settings.screenshot_dir, self.settings.html_snapshot_dir]:
            if not directory.exists():
                continue
            for date_dir in directory.iterdir():
                if date_dir.is_dir():
                    try:
                        dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
                        if dir_date < cutoff:
                            shutil.rmtree(date_dir)
                            removed += 1
                    except ValueError:
                        continue

        logger.info("cleanup_complete", removed_dirs=removed)
        return removed
