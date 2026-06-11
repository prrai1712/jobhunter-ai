"""Unit tests for Telegram formatters."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from src.telegram.formatters import escape_md, format_job_card, format_stats_table


def test_escape_md() -> None:
    # Test standard special characters
    assert escape_md("Hello! (World)") == r"Hello\! \(World\)"
    # Test text containing no special chars
    assert escape_md("simple text") == "simple text"


def test_format_stats_table() -> None:
    headers = ["Name", "Count"]
    rows = [["Google", "12"], ["Meta", "5"]]

    table = format_stats_table(headers, rows)
    # Monospace backticks wrapper
    assert table.startswith("```\n")
    assert table.endswith("\n```")
    assert "Google | 12" in table
    assert "Meta   | 5 " in table


def test_format_job_card() -> None:
    job = MagicMock()
    job.title = "Software Engineer"
    job.location = "Bangalore"
    job.salary_estimate = 22.5
    job.match_score = 92.0
    job.status.value = "new"
    job.apply_url = "https://example.com/apply"
    job.id = "12345678-abcd-1234-abcd-123456789012"

    card = format_job_card(job)
    assert "Software Engineer" in card
    assert "Bangalore" in card
    assert "22.5L" in card
    assert "92%" in card
    assert "new" in card
    assert "https://example.com/apply" in card
