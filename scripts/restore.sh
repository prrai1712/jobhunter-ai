#!/usr/bin/env bash

# ==============================================================================
# JobHunter AI Database Restore Script
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
    exit 1
}

# Ensure file is provided
if [ $# -ne 1 ]; then
    error "Usage: $0 <path_to_backup_file.sql>"
fi

BACKUP_FILE="$1"

# Check if file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    error "Backup file not found: ${BACKUP_FILE}"
fi

# Determine docker compose command
DC_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    if command -v docker-compose &> /dev/null; then
        DC_CMD="docker-compose"
    else
        error "Docker Compose not found. Cannot run restore."
    fi
fi

# Load database credentials from .env
if [ -f .env ]; then
    DB_USER=$(grep -E "^DB_USER=" .env | cut -d'=' -f2- || echo "jobhunter")
    DB_NAME=$(grep -E "^DB_NAME=" .env | cut -d'=' -f2- || echo "jobhunter_db")
else
    DB_USER="jobhunter"
    DB_NAME="jobhunter_db"
fi

warn "This will overwrite all current database data. Are you sure you want to proceed? (y/N)"
read -r response
if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    log "Restoration cancelled."
    exit 0
fi

log "Stopping app service to terminate active database connections..."
$DC_CMD stop app || true

log "Recreating database inside PostgreSQL container..."
# Drop active connections, terminate DB session, recreate DB
docker exec -t jobhunter_postgres psql -U "${DB_USER}" -d postgres -c \
    "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${DB_NAME}' AND pid <> pg_backend_pid();" || true

docker exec -t jobhunter_postgres psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker exec -t jobhunter_postgres psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

log "Restoring backup from ${BACKUP_FILE}..."
docker exec -i jobhunter_postgres psql -U "${DB_USER}" -d "${DB_NAME}" < "${BACKUP_FILE}"

log "Starting app service..."
$DC_CMD start app

log "Restoration complete! JobHunter AI has been restarted."
