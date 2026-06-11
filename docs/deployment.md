# Deployment Guide — Oracle Cloud Free Tier

This document provides a step-by-step walkthrough to deploy **JobHunter AI** to an Oracle Cloud Free Tier Virtual Machine (ARM Ampere A1 instance or AMD compute instance).

---

## 1. Instance Creation

When setting up your compute instance in the Oracle Cloud Console:
1. **Operating System**: Choose **Ubuntu 22.04 LTS** (highly recommended for compatibility with Playwright/Chromium dependencies).
2. **Shape**: Choose **VM.Standard.A1.Flex** (Ampere ARM processor). You can assign up to 4 OCPUs and 24 GB of RAM under the Always Free Tier.
3. **Networking**: Assign a public IPv4 address and download the generated private SSH key.
4. **Boot Volume**: Select the default size or increase it up to 200 GB.

---

## 2. Server Configuration

Log in to your compute instance via SSH:
```bash
ssh -i /path/to/ssh_key.key ubuntu@YOUR_INSTANCE_IP
```

Clone the repository and run the setup script:
```bash
git clone https://github.com/yourusername/jobhunter-ai.git
cd jobhunter-ai
sudo ./scripts/setup_oracle.sh
```

The script will:
- Set up a **4GB swapfile** (critical to prevent OOM errors when running Chromium instances inside the container).
- Install system packages, Docker CE, and Docker Compose.
- Configure local firewalls (UFW/iptables) to allow access to PostgreSQL (port `5432`).

Add your user to the Docker group so you can execute docker commands without `sudo`:
```bash
sudo usermod -aG docker ubuntu
```
**Log out and log back in** for changes to take effect.

---

## 3. Virtual Cloud Network (VCN) Security Lists

By default, Oracle Cloud blocks incoming traffic on the virtual network level. If you need to access the database externally (e.g., via DBeaver on localhost):
1. In the Oracle Cloud Console, navigate to **Compute** -> **Instances** -> **Instance Details**.
2. Click on the **Virtual Cloud Network** link.
3. Select **Security Lists** in the left sidebar, then click on the **Default Security List**.
4. Click **Add Ingress Rules**:
   - **Source CIDR**: `0.0.0.0/0` (or your personal IP address for better security)
   - **IP Protocol**: `TCP`
   - **Destination Port Range**: `5432`
   - **Description**: PostgreSQL database port

---

## 4. Configuring `.env` File

Create your production configuration file:
```bash
cp .env.example .env
nano .env
```

### Essential Parameters to Configure:

#### Telegram Settings
- `TELEGRAM_BOT_TOKEN`: Token obtained from [@BotFather](https://t.me/BotFather).
- `ALLOWED_TELEGRAM_USER_ID`: Your exact user ID (obtained from [@userinfobot](https://t.me/userinfobot)). If any other account attempts to interact with the bot, they will be blocked.

#### Database Settings
- `DB_USER`: Custom postgres username.
- `DB_PASSWORD`: Set a secure, long password.
- `DB_NAME`: Database name (e.g., `jobhunter_prod`).

#### Candidate Profile
Configure your contact information, target positions, skills, and experience to seed the matching engine:
- `CANDIDATE_NAME`: Your full name.
- `CANDIDATE_EMAIL`: Your application email.
- `CANDIDATE_PHONE`: Your phone number.
- `CANDIDATE_COUNTRY`: Country of residence.
- `CANDIDATE_EXPERIENCE_YEARS`: (integer) E.g., `5`.
- `CANDIDATE_SKILLS`: Comma-separated list of skills matching canonical skills in `skills_db.py`. E.g., `Python,Django,PostgreSQL,Docker,Kubernetes,AWS`.
- `CANDIDATE_TARGET_ROLES`: Comma-separated list of keywords representing your target job titles. E.g., `Backend Engineer,Software Engineer,Python Developer`.

#### Job Search Rules
- `MIN_SALARY_LPA`: Minimum threshold for automatic application (in Lakhs Per Annum). E.g., `18`.
- `MIN_MATCH_SCORE`: Minimum AI evaluation match score (0-100) to apply. E.g., `85`.

---

## 5. Startup & Deployment

Once configured, deploy the system stack:
```bash
./scripts/deploy.sh
```

This starts:
1. `jobhunter_postgres`: Main PostgreSQL database storage.
2. `jobhunter_backup`: Periodic cron container that saves SQL dumps inside `./data/backups/`.
3. `jobhunter_app`: JobHunter AI core service containing the bot, scrapers, scorers, and browsers.

### Verification Steps
To ensure everything initialized correctly:
1. Inspect running containers:
   ```bash
   docker compose ps
   ```
2. Inspect application startup logs to verify migrations completed and the bot is polling:
   ```bash
   docker compose logs -f app
   ```
3. Open Telegram, search for your bot name, and send `/start`.
4. Run `/database_health` and `/system_status` to check connection pools.
