"""Playwright browser manager — headless Chromium with anti-detection and utilities."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from src.core.config.settings import get_settings

logger = structlog.get_logger(__name__)


class PlaywrightBrowserManager:
    """Manages a headless Chromium browser instance for application automation.

    Features:
    - Singleton pattern (one browser per process)
    - Anti-detection settings
    - Screenshot capture
    - HTML snapshot capture
    - Page timeout handling
    """

    _instance: PlaywrightBrowserManager | None = None
    _browser: Any = None
    _playwright: Any = None

    def __init__(self) -> None:
        self.screenshot_dir = get_settings().storage.screenshot_dir
        self.snapshot_dir = get_settings().storage.html_snapshot_dir

    @classmethod
    async def get_instance(cls) -> PlaywrightBrowserManager:
        """Get or create the singleton browser manager."""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance._start_browser()
        return cls._instance

    async def _start_browser(self) -> None:
        """Initialize the Playwright browser."""
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                ],
            )
            logger.info("browser_started")
        except Exception as e:
            logger.error("browser_start_failed", error=str(e))
            raise

    async def new_page(self) -> Any:
        """Create a new browser page with anti-detection settings."""
        if self._browser is None:
            await self._start_browser()

        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Asia/Kolkata",
        )

        # Add anti-detection scripts
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
        """)

        page = await context.new_page()
        page.set_default_timeout(30000)
        return page

    async def take_screenshot(
        self,
        page: Any,
        job_id: str,
        step: str,
    ) -> str:
        """Capture a screenshot and save to storage.

        Returns:
            File path of the saved screenshot.
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        day_dir = self.screenshot_dir / timestamp
        day_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{job_id}_{step}_{datetime.now().strftime('%H%M%S')}.png"
        filepath = day_dir / filename

        try:
            await page.screenshot(path=str(filepath), full_page=True)
            logger.debug("screenshot_saved", path=str(filepath))
        except Exception as e:
            logger.warning("screenshot_failed", error=str(e))
            return ""

        return str(filepath)

    async def save_html_snapshot(
        self,
        page: Any,
        job_id: str,
    ) -> str:
        """Capture an HTML snapshot of the current page.

        Returns:
            File path of the saved HTML.
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        day_dir = self.snapshot_dir / timestamp
        day_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{job_id}_{datetime.now().strftime('%H%M%S')}.html"
        filepath = day_dir / filename

        try:
            html = await page.content()
            filepath.write_text(html, encoding="utf-8")
            logger.debug("html_snapshot_saved", path=str(filepath))
        except Exception as e:
            logger.warning("html_snapshot_failed", error=str(e))
            return ""

        return str(filepath)

    async def close(self) -> None:
        """Shut down the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        PlaywrightBrowserManager._instance = None
        logger.info("browser_closed")

    async def fill_and_submit_form(
        self,
        page: Any,
        fields: dict[str, str],
        submit_selector: str = 'button[type="submit"]',
    ) -> bool:
        """Generic form filler — fills input fields and submits.

        Args:
            page: Playwright page.
            fields: Dict mapping CSS selectors to values.
            submit_selector: CSS selector for the submit button.

        Returns:
            True if form submission appeared successful.
        """
        try:
            for selector, value in fields.items():
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        await element.fill(value)
                        await asyncio.sleep(0.3)  # Human-like delay
                except Exception:
                    logger.debug("field_not_found", selector=selector)

            # Click submit
            submit = await page.wait_for_selector(submit_selector, timeout=5000)
            if submit:
                await submit.click()
                await asyncio.sleep(2)  # Wait for submission
                return True

        except Exception as e:
            logger.warning("form_submit_failed", error=str(e))

        return False
