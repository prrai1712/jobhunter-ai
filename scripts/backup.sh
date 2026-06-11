#!/usr/bin/env bash

# ==============================================================================
# JobHunter AI Manual Backup Script
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
    exit 1
}

# Determine docker compose command
DC_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    if command -v docker-compose &> /dev/null; then
        DC_CMD="docker-compose"
    else
        error "Docker Compose not found. Cannot run backup."
    fi
fi

# Check if postgres container is running
if ! docker ps | grep -q jobhunter_postgres; then
    error "PostgreSQL container (jobhunter_postgres) is not running."
fi

# Load database credentials from .env
if [ -f .env ]; then
    # Parse DB credentials from .env without exporting everything
    DB_USER=$(grep -E "^DB_USER=" .env | cut -d'=' -f2- || echo "jobhunter")
    DB_NAME=$(grep -E "^DB_NAME=" .env | cut -d'=' -f2- || echo "jobhunter_db")
else
    DB_USER="jobhunter"
    DB_NAME="jobhunter_db"
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./data/backups"
BACKUP_FILE="${BACKUP_DIR}/manual_backup_${TIMESTAMP}.sql"

log "Creating local backup folder: ${BACKUP_DIR}..."
mkdir -p "${BACKUP_DIR}"

log "Running pg_dump inside postgres container..."
docker exec -t jobhunter_postgres pg_dump -U "${DB_USER}" -d "${DB_NAME}" > "${BACKUP_FILE}"

if [ -f "${BACKUP_FILE}" ] && [ -s "${BACKUP_FILE}" ]; then
    log "Backup successfully created: ${BACKUP_FILE}"
    # Keep only the last 15 manual backups
    log "Cleaning up older manual backups..."
    ls -tp "${BACKUP_DIR}"/manual_backup_*.sql | grep -v "/$" | tail -n +16 | xargs -I {} rm -- {} || true
    log "Cleanup complete."
else
    error "Backup failed or file is empty."
fi
