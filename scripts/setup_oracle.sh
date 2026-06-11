#!/usr/bin/env bash

# ==============================================================================
# JobHunter AI Oracle Cloud Instance Setup Script
# ==============================================================================

set -euo pipefail

# Output styling
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

# Require sudo / root execution
if [ "$EUID" -ne 0 ]; then
    error "Please run this script as root (sudo)."
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$ID
else
    OS_NAME="unknown"
fi

log "Detected OS: ${OS_NAME}"

# 1. Setup SWAP Space (Critical for ARM / 1GB VM instances running Chromium)
if [ ! -f /swapfile ]; then
    log "Setting up 4GB Swap Space..."
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    log "Swap space successfully created."
else
    warn "Swap space (/swapfile) already exists. Skipping."
fi

# 2. Update packages and install prerequisites
log "Updating system packages and installing prerequisites..."
if [[ "$OS_NAME" == "ubuntu" || "$OS_NAME" == "debian" ]]; then
    apt-get update && apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        software-properties-common \
        iptables-persistent \
        git \
        ufw
elif [[ "$OS_NAME" == "centos" || "$OS_NAME" == "rhel" || "$OS_NAME" == "oracle" || "$OS_NAME" == "rocky" ]]; then
    yum update -y && yum install -y \
        curl \
        git \
        iptables-services
else
    warn "Unsupported OS for automatic package installation. Please ensure Docker, Docker Compose, git, and curl are installed manually."
fi

# 3. Install Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    log "Installing Docker CE..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable --now docker
    rm get-docker.sh
    log "Docker CE installed successfully."
else
    log "Docker is already installed."
fi

if ! docker compose version &> /dev/null; then
    log "Installing Docker Compose plugin..."
    if [[ "$OS_NAME" == "ubuntu" || "$OS_NAME" == "debian" ]]; then
        apt-get update && apt-get install -y docker-compose-plugin
    else
        # Fallback to manual download
        DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
        mkdir -p "$DOCKER_CONFIG/cli-plugins"
        curl -SL https://github.com/docker/compose/releases/download/v2.26.0/docker-compose-linux-x86_64 -o "$DOCKER_CONFIG/cli-plugins/docker-compose"
        chmod +x "$DOCKER_CONFIG/cli-plugins/docker-compose"
    fi
    log "Docker Compose installed successfully."
else
    log "Docker Compose is already installed."
fi

# 4. Configure Firewalls (Oracle Cloud has strict iptables rules by default)
log "Configuring firewalls to open ports..."
if [[ "$OS_NAME" == "ubuntu" ]]; then
    # Oracle Ubuntu defaults to iptables rules that drop everything
    # Check if iptables has custom Oracle rules
    if iptables -L INPUT -n | grep -q "REJECT"; then
        log "Adjusting iptables for Oracle Cloud..."
        # Open typical ports if user needs database access externally
        iptables -I INPUT 6 -p tcp --dport 5432 -j ACCEPT -m comment --comment "postgres" || true
        netfilter-persistent save || true
    fi
    # Configure UFW
    ufw allow ssh
    ufw allow 5432/tcp
    ufw --force enable
elif [[ "$OS_NAME" == "oracle" || "$OS_NAME" == "centos" ]]; then
    # Firewalld settings
    if systemctl is-active --quiet firewalld; then
        firewall-cmd --permanent --add-port=5432/tcp
        firewall-cmd --reload
    fi
fi

log "System setup complete!"
log "Ensure you add any non-root user (e.g. 'ubuntu' or 'opc') to the docker group:"
log "  sudo usermod -aG docker \$USER"
log "Then log out and log back in to apply changes."
