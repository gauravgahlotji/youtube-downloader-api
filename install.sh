#!/usr/bin/env bash

# ==============================================================================
# Enterprise YouTube Downloader API Platform - One-Click Production Installer
# Compatible with Ubuntu 22.04 LTS & Ubuntu 24.04 LTS
# ==============================================================================

set -e

export DEBIAN_FRONTEND=noninteractive

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "=================================================================="
echo "  Enterprise YouTube Downloader API Platform - Automated Installer"
echo "=================================================================="
echo -e "${NC}"

# 1. Root permission check
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[ERROR] Please run this installer with root or sudo:${NC}"
  echo -e "${YELLOW}        sudo bash install.sh   OR   sudo ./install.sh${NC}"
  exit 1
fi

# 2. OS Compatibility Check
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        echo -e "${YELLOW}[WARNING] This script is optimized for Ubuntu. Detected OS: $NAME${NC}"
    fi
fi

# 3. Clean APT cache & temporary files to free up disk space
apt-get clean 2>/dev/null || true
rm -f /swapfile 2>/dev/null || true

# Stop conflicting old docker containers & processes on port 8000
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
pkill -9 -f gunicorn 2>/dev/null || true
pkill -9 -f uvicorn 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true

# 4. Smart Swap Space Allocation based on available disk space
TOTAL_SWAP=$(free -m | awk '/^Swap:/{print $2}')
if [ "${TOTAL_SWAP:-0}" -eq 0 ]; then
    FREE_MB=$(df -m / | awk 'NR==2 {print $4}')
    echo -e "${YELLOW}[MEMORY] Checking free disk space: ${FREE_MB} MB available.${NC}"
    
    SWAP_SIZE=0
    if [ "$FREE_MB" -gt 3000 ]; then
        SWAP_SIZE=2048
    elif [ "$FREE_MB" -gt 1500 ]; then
        SWAP_SIZE=1024
    elif [ "$FREE_MB" -gt 700 ]; then
        SWAP_SIZE=512
    fi

    if [ "$SWAP_SIZE" -gt 0 ]; then
        echo -e "${YELLOW}[MEMORY] Allocating ${SWAP_SIZE}MB swap space to prevent OOM crash...${NC}"
        (fallocate -l ${SWAP_SIZE}M /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=${SWAP_SIZE} 2>/dev/null || true)
        chmod 600 /swapfile 2>/dev/null || true
        mkswap /swapfile 2>/dev/null || true
        swapon /swapfile 2>/dev/null || true
        if ! grep -q '/swapfile' /etc/fstab; then
            echo '/swapfile none swap sw 0 0' >> /etc/fstab 2>/dev/null || true
        fi
        echo -e "${GREEN}[MEMORY] ${SWAP_SIZE}MB Swap space configured successfully.${NC}"
    else
        echo -e "${YELLOW}[MEMORY] Limited disk space. Skipping Swap creation to preserve disk space.${NC}"
    fi
fi

INSTALL_DIR="$(pwd)"
echo -e "${BLUE}[STEP 1/9] Setting up installation directory: ${INSTALL_DIR}${NC}"

# 5. Install System Packages
echo -e "${BLUE}[STEP 2/9] Installing system packages & dependencies (FFmpeg, Python3, Nginx, UFW, Curl, Psmisc)...${NC}"
apt-get update -y
apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    curl \
    wget \
    git \
    unzip \
    nginx \
    ufw \
    psmisc \
    ca-certificates

# Install Deno JS runtime non-interactively for yt-dlp engine if missing
if ! command -v deno &> /dev/null; then
    echo -e "${BLUE}Installing Deno JS runtime for yt-dlp core...${NC}"
    curl -fsSL https://deno.land/install.sh | sh -s -- -y 2>/dev/null || true
    if [ -d "$HOME/.deno/bin" ]; then
        export PATH="$HOME/.deno/bin:$PATH"
    fi
fi

# 6. Create Python Virtual Environment
echo -e "${BLUE}[STEP 3/9] Creating Python Virtual Environment...${NC}"
VENV_DIR="${INSTALL_DIR}/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "${VENV_DIR}/bin/activate"
pip install --no-cache-dir --upgrade pip setuptools wheel
pip uninstall -y app youtube-downloader-api yt-dlp-api 2>/dev/null || true
rm -rf "${VENV_DIR}/lib/python"*/site-packages/app 2>/dev/null || true
find "${INSTALL_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 7. Install Project Dependencies
echo -e "${BLUE}[STEP 4/9] Installing Python dependencies from requirements.txt...${NC}"
pip install --no-cache-dir -r "${INSTALL_DIR}/requirements.txt"
pip install --no-cache-dir -U yt-dlp

# Ensure downloads directory exists with correct permissions
mkdir -p "${INSTALL_DIR}/downloads"
chmod 775 "${INSTALL_DIR}/downloads"

# 8. Generate .env Configuration File
echo -e "${BLUE}[STEP 5/9] Configuring environment variables (.env)...${NC}"
ENV_FILE="${INSTALL_DIR}/.env"
if [ ! -f "$ENV_FILE" ]; then
    GEN_API_KEY="yt_live_$(openssl rand -hex 10)"
    GEN_SECRET_KEY="sec_$(openssl rand -hex 16)"
    cat <<EOF > "$ENV_FILE"
API_TITLE="Enterprise YouTube Downloader API Platform"
API_VERSION="1.0.0"
API_KEY="${GEN_API_KEY}"
SECRET_KEY="${GEN_SECRET_KEY}"
DOWNLOAD_DIR="${INSTALL_DIR}/downloads"
TEMP_FILE_TTL_MINUTES=60
MAX_CONCURRENT_DOWNLOADS=10
SECURITY_ENFORCE_SIGNATURE=false
RATE_LIMIT_REQUESTS_PER_MINUTE=120
EOF
    echo -e "${GREEN}Generated new .env file with secure random keys.${NC}"
else
    echo -e "${YELLOW}.env file already exists, retaining existing settings.${NC}"
fi

# Extract API_KEY and SECRET_KEY for summary display
API_KEY_VAL=$(grep "^API_KEY=" "$ENV_FILE" | cut -d '=' -f2 | tr -d '"')
SECRET_KEY_VAL=$(grep "^SECRET_KEY=" "$ENV_FILE" | cut -d '=' -f2 | tr -d '"')

# Kill any leftover old standalone Gunicorn/Uvicorn processes & free Port 8000
pkill -9 -f gunicorn 2>/dev/null || true
pkill -9 -f uvicorn 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true

# 9. Create & Configure Systemd Service
echo -e "${BLUE}[STEP 6/9] Creating Systemd service (yt-dlp-api.service)...${NC}"
SERVICE_FILE="/etc/systemd/system/yt-dlp-api.service"

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Enterprise YouTube Downloader API Engine
After=network.target

[Service]
User=root
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=${VENV_DIR}/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000 --timeout 600
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable yt-dlp-api.service
systemctl restart yt-dlp-api.service

# 10. Configure Nginx Reverse Proxy
echo -e "${BLUE}[STEP 7/9] Configuring Nginx reverse proxy...${NC}"
NGINX_CONF="/etc/nginx/sites-available/yt-dlp-api"

cat <<EOF > "$NGINX_CONF"
server {
    listen 80;
    server_name _;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        send_timeout 600s;
    }
}
EOF

# Clean conflicting site symlinks in sites-enabled
rm -f /etc/nginx/sites-enabled/* 2>/dev/null || true
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/yt-dlp-api

nginx -t
systemctl restart nginx

# 11. Configure Firewall (UFW)
echo -e "${BLUE}[STEP 8/9] Configuring UFW Firewall (Ports 22, 80, 443)...${NC}"
ufw allow 22/tcp || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
ufw --force enable || true

# 12. Deployment Verification
echo -e "${BLUE}[STEP 9/9] Performing deployment health check verification...${NC}"
sleep 3

HEALTH_CHECK=$(curl -s http://127.0.0.1:8000/health || echo "FAILED")

if [[ "$HEALTH_CHECK" == *"healthy"* ]]; then
    echo -e "${GREEN}=================================================================="
    echo -e "       SUCCESS! Enterprise Download API Platform Deployed!        "
    echo -e "==================================================================${NC}"
    echo -e ""
    echo -e "${CYAN}📌 ACCESS URLS:${NC}"
    echo -e "   - Developer Dashboard:  http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')/dashboard"
    echo -e "   - OpenAPI / Swagger:    http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')/docs"
    echo -e "   - API Base Endpoint:    http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')/api/v1"
    echo -e ""
    echo -e "${CYAN}🔑 API CREDENTIALS FOR LARAVEL / CLIENTS:${NC}"
    echo -e "   - API KEY:    ${API_KEY_VAL}"
    echo -e "   - SECRET KEY: ${SECRET_KEY_VAL}"
    echo -e ""
    echo -e "${CYAN}🛠 SYSTEMD COMMANDS:${NC}"
    echo -e "   - Check Status: sudo systemctl status yt-dlp-api"
    echo -e "   - View Logs:    sudo journalctl -u yt-dlp-api -f"
    echo -e "   - Restart API:  sudo systemctl restart yt-dlp-api"
    echo -e ""
else
    echo -e "${YELLOW}[WARNING] API service started, but health check response was: ${HEALTH_CHECK}${NC}"
    echo -e "Check systemd logs using: sudo journalctl -u yt-dlp-api -f"
fi
