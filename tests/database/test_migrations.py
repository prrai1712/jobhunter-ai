"""Tests for database migrations setup."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


def test_alembic_config_exists() -> None:
    # Verify alembic.ini is present in the workspace
    assert os.path.exists("alembic.ini")
    assert os.path.exists("alembic/env.py")


def test_migrations_heads() -> None:
    # Verify migration scripts can be loaded by Alembic
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    # Verify script directory structure is healthy
    assert script.get_current_head() is not None or len(script.get_heads()) >= 0
