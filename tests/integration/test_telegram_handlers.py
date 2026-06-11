"""Integration tests for Telegram command handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config.settings import get_settings
from src.telegram.handlers.system import (
    help_command,
    start_command,
    start_system_command,
)


@pytest.mark.asyncio
async def test_start_command(db_session: AsyncSession) -> None:
    # 1. Setup mock update and context
    update = MagicMock()
    update.effective_user.id = 123456789 # Matches test_settings allowed ID
    update.effective_user.username = "testuser"
    update.effective_user.full_name = "Test User"
    update.effective_chat.id = 987654321
    update.message = AsyncMock()
    update.message.text = "/start"

    context = MagicMock()

    # 2. Patch database connection in middleware to use test session
    @pytest.fixture(autouse=True)
    def setup_session_mocker():
        pass

    async def mock_get_session():
        yield db_session

    with patch("src.telegram.middleware.get_async_session", mock_get_session), \
         patch("src.telegram.handlers.system.get_async_session", mock_get_session):

        # Execute command
        await start_command(update, context)

        # Assert correct reply was sent
        update.message.reply_text.assert_called_once()
        args, kwargs = update.message.reply_text.call_args
        assert "Welcome to JobHunter" in args[0]
        assert kwargs.get("parse_mode") == "MarkdownV2"


@pytest.mark.asyncio
async def test_start_system_command(db_session: AsyncSession) -> None:
    update = MagicMock()
    update.effective_user.id = 123456789
    update.effective_user.username = "testuser"
    update.effective_user.full_name = "Test User"
    update.effective_chat.id = 987654321
    update.message = AsyncMock()
    update.message.text = "/start_system"

    context = MagicMock()

    async def mock_get_session():
        yield db_session

    with patch("src.telegram.middleware.get_async_session", mock_get_session), \
         patch("src.telegram.handlers.system.get_async_session", mock_get_session):

        # Execute system start
        await start_system_command(update, context)

        # Assert system transitioned to running and replied
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        assert "System started" in args[0]


@pytest.mark.asyncio
async def test_help_command() -> None:
    update = MagicMock()
    update.effective_user.id = 123456789
    update.message = AsyncMock()
    update.message.text = "/help"

    context = MagicMock()

    # Help command doesn't touch the DB, so we only need to bypass the auth logging
    with patch("src.telegram.middleware.get_async_session"):
        await help_command(update, context)
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        assert "Command Center" in args[0]
