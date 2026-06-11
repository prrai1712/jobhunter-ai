#!/usr/bin/env bash

# ==============================================================================
# JobHunter AI Deployment Script
# ==============================================================================

set -euo pipefail

# Output styling
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0;36m' # Cyan default

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

# 1. Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose is not installed. Run setup_oracle.sh first."
fi

# Define docker compose command
DC_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    DC_CMD="docker-compose"
fi

# 2. Check if .env file exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        log "Copying .env.example to .env..."
        cp .env.example .env
        warn "Created .env from template. Please configure it before starting."
    else
        error "No .env file found and .env.example is missing."
    fi
fi

# 3. Pull latest changes (if in git repository)
if [ -d .git ]; then
    log "Pulling latest code from git repository..."
    git pull || warn "Could not pull latest changes from git. Proceeding with current local files."
fi

# 4. Build and restart containers
log "Rebuilding and restarting services..."
$DC_CMD down --remove-orphans
$DC_CMD up --build -d

# 5. Verify service health
log "Verifying services status..."
sleep 5
$DC_CMD ps

# 6. Check database logs to confirm migrations ran successfully
log "Checking application startup logs..."
$DC_CMD logs --tail=50 app

log "Deployment complete! JobHunter AI is running."
