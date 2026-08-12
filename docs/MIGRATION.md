# Migration Runbook: VM Free → New VM

**Target:** Complete migration in **< 30 minutes**  
**Last tested:** 2026-08-12  
**Version:** 1.0

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] **New VM ready** (Ubuntu 22.04/24.04, 4GB+ RAM, 50GB+ disk)
- [ ] **Docker + Docker Compose installed**
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  # Logout/login or: newgrp docker
  docker compose version
  ```
- [ ] **GitHub CLI authenticated**
  ```bash
  gh auth login
  gh auth status
  ```
- [ ] **rclone configured** (OneDrive + R2)
  ```bash
  rclone config
  rclone listremotes
  # Should show: onedrive:  r2:
  ```
- [ ] **Secrets manager access** (1Password CLI or Bitwarden CLI)
  ```bash
  # 1Password
  op signin
  op whoami
  
  # OR Bitwarden
  bw login
  bw unlock
  ```

---

## 🚀 Step-by-Step Migration (Target: < 30 min)

### 1. Clone Repository (2 min)
```bash
gh repo clone <your-username>/mech-automation ~/mech-automation
cd ~/mech-automation
git status  # Should be clean
```

### 2. Restore Secrets (3 min)

**Option A: 1Password (Recommended)**
```bash
# Install 1Password CLI if needed
# op inject -i config/.env.example -o config/.env

# Or manual:
export OPENROUTER_API_KEY=$(op read "op://Private/OpenRouter_API_Key/credential")
export TG_BOT_TOKEN=$(op read "op://Private/TG_Bot_Token/credential")
export TG_CHAT_ID=$(op read "op://Private/TG_Chat_ID/credential")
export CRYPTOPANIC_TOKEN=$(op read "op://Private/CryptoPanic_Token/credential")
export N8N_ENCRYPTION_KEY=$(op read "op://Private/N8N_Encryption_Key/credential")
export N8N_BASIC_AUTH_PASSWORD=$(op read "op://Private/N8N_Password/credential")
export R2_BUCKET=$(op read "op://Private/R2_Bucket/credential")

# Create .env
envsubst < config/.env.example > config/.env
```

**Option B: Bitwarden**
```bash
bw unlock
export OPENROUTER_API_KEY=$(bw get password "OpenRouter_API_Key")
# ... repeat for all secrets
envsubst < config/.env.example > config/.env
```

**Option C: Manual (if no secrets manager)**
```bash
cp config/.env.example config/.env
# Edit config/.env with your editor, fill all values
nano config/.env
```

### 3. Restore Data (10 min)
```bash
# Create data directories
mkdir -p data/sqlite data/n8n data/hermes

# Restore SQLite DBs
rclone copy onedrive:Backups/sqlite/ ./data/sqlite/ --progress
rclone copy r2:<bucket>/Backups/sqlite/ ./data/sqlite/ --progress  # If R2 configured

# Restore n8n data
rclone copy onedrive:Backups/n8n/ ./data/n8n/ --progress

# Restore Hermes data
rclone copy onedrive:Backups/hermes/ ~/.hermes/ --progress

# Verify restores
ls -la data/sqlite/
ls -la data/n8n/
ls -la ~/.hermes/
```

### 4. Start Services (5 min)
```bash
# Build and start all services
docker compose -f infra/docker-compose.yml up -d --build

# Verify all containers running
docker compose -f infra/docker-compose.yml ps

# Check logs
docker compose -f infra/docker-compose.yml logs -f --tail=50
```

### 5. Verify Health (5 min)
```bash
# Wait 30 seconds for services to fully start
sleep 30

# Check crypto news bot (run manually once)
docker compose -f infra/docker-compose.yml run --rm crypto-news \
  python scripts/crypto_news_scorer.py --dry-run

# Check n8n
curl -s http://localhost:5678/healthz

# Check backup script
docker compose -f infra/docker-compose.yml run --rm backup \
  python scripts/backup.py --dry-run

# Check rclone
rclone listremotes
rclone copy ./data/sqlite/ onedrive:Test/restore-$(date +%s) --dry-run
```

### 6. Enable Cronjobs (2 min)
```bash
# Install cronjobs via Hermes (if Hermes installed)
# hermes cronjob create --name crypto-morning-news --schedule "0 6 * * *" --script scripts/crypto_news_scorer.py --skills hermes-agent --toolsets terminal,web
# hermes cronjob create --name daily-backup --schedule "0 */6 * * *" --script scripts/backup.py --toolsets terminal

# OR use system cron (if not using Hermes)
crontab -l > /tmp/cron_backup_$(date +%s)
cat >> /tmp/cron_new << 'EOF'
# Crypto Morning News - Daily 6:00 AM
0 6 * * * cd ~/mech-automation && docker compose -f infra/docker-compose.yml run --rm crypto-news python scripts/crypto_news_scorer.py >> /app/data/crypto_news_cron.log 2>&1

# Backup - Every 6 hours
0 */6 * * * cd ~/mech-automation && docker compose -f infra/docker-compose.yml run --rm backup python scripts/backup.py >> /app/data/backup_cron.log 2>&1
EOF
crontab /tmp/cron_new
crontab -l
```

### 7. Test End-to-End (3 min)
```bash
# Send test Telegram
curl -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TG_CHAT_ID}" \
  -d text="🧪 Migration test - $(date)"

# Trigger manual backup
docker compose -f infra/docker-compose.yml run --rm backup python scripts/backup.py

# Check OneDrive for new backup
rclone lsl onedrive:Backups/sqlite/ | tail -5
```

---

## ✅ Post-Migration Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| All containers running | `docker compose ps` | 3-4 containers Up |
| Crypto bot runs | Manual test | No errors, Telegram test msg |
| n8n accessible | `curl localhost:5678/healthz` | HTTP 200 |
| Backup works | Manual run | Files in OneDrive/R2 |
| rclone remotes | `rclone listremotes` | onedrive:, r2: |
| Cronjobs installed | `crontab -l` | 2+ entries |
| Telegram alerts | Test message | Received in chat |
| Disk space | `df -h /` | > 20% free |

---

## 🔄 Rollback Plan (if migration fails)

```bash
# 1. Stop new VM services
docker compose -f ~/mech-automation/infra/docker-compose.yml down

# 2. If old VM still alive - use it
#    No action needed, old VM continues running

# 3. If old VM gone - restore on another fresh VM
#    Repeat this runbook from Step 1

# 4. Emergency: Restore from rclone directly on any machine
mkdir -p /tmp/emergency-restore
rclone copy onedrive:Backups/sqlite/ /tmp/emergency-restore/sqlite/
rclone copy onedrive:Backups/n8n/ /tmp/emergency-restore/n8n/
# Point scripts to /tmp/emergency-restore/...
```

---

## 📞 Emergency Contacts & Resources

| Resource | URL/Command |
|----------|-------------|
| GitHub Repo | `gh repo view <user>/mech-automation` |
| Docker Hub | `docker.io` |
| rclone docs | `rclone.org/docs` |
| n8n docs | `docs.n8n.io` |
| Hermes docs | `hermes-agent.nousresearch.com/docs` |
| Telegram Bot API | `core.telegram.org/bots/api` |

---

## 📝 Post-Migration Notes Template

```
Migration Date: ___________
From VM: ___________ (IP: ___________)
To VM: ___________ (IP: ___________)
Duration: ___________ minutes
Issues: ___________
Resolved: ___________
Next backup test: ___________
```

**Sign-off:** ________________________  
**Date:** ________________________