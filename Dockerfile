# ==============================================================================
# Production Dockerfile for JobHunter AI
# ==============================================================================

# Use Python 3.12 slim-bookworm as base for minimized image size and security
FROM python:3.12-slim-bookworm AS builder

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml to install dependencies first (Docker cache layer optimization)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install .


# Final runtime stage
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (Playwright / Chromium dependencies, libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    # Required chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Install Playwright Chromium browser binary only
RUN playwright install chromium

# Create a non-root system user and set permissions
RUN groupadd -g 10001 jobhunter && \
    useradd -u 10001 -g jobhunter -s /bin/bash -m jobhunter

# Set up storage directory structure inside container and grant access
RUN mkdir -p /app/data/resumes /app/data/screenshots /app/data/html_snapshots /app/data/reports /app/data/exports && \
    chown -R jobhunter:jobhunter /app

# Copy source code and config templates
COPY --chown=jobhunter:jobhunter alembic.ini ./alembic.ini
COPY --chown=jobhunter:jobhunter alembic/ ./alembic/
COPY --chown=jobhunter:jobhunter src/ ./src/

# Switch to non-root user for security
USER jobhunter

# Volume for persistent files and logs
VOLUME ["/app/data"]

# Healthcheck to verify process liveliness
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "from src.core.database.engine import check_database_health; import asyncio; res = asyncio.run(check_database_health()); exit(0 if res.get('status') == 'healthy' else 1)"

# Start JobHunter AI
CMD ["python", "-m", "src.main"]
