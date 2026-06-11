"""Structured logging configuration using structlog."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog

from src.core.config.settings import get_settings


def setup_logging() -> None:
    """Configure structlog with JSON or console output based on environment."""
    settings = get_settings()
    log_level = getattr(logging, settings.logging.log_level.upper(), logging.INFO)

    # Ensure log directory exists
    log_file = settings.logging.log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Shared processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.logging.log_format == "json":
        # JSON output for production
        renderer = structlog.processors.JSONRenderer()
    else:
        # Console output for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)  # type: ignore[assignment]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Quiet noisy libraries
    for lib in ["httpx", "httpcore", "asyncio", "apscheduler"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    structlog.get_logger().info(
        "logging_configured",
        level=settings.logging.log_level,
        format=settings.logging.log_format,
        file=str(log_file),
    )
