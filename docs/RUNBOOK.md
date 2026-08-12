# Operations Runbook: mech-automation

**Version:** 1.0  
**Last updated:** 2026-08-12  
**Environment:** Docker Compose on Ubuntu VM

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DOCKER NETWORK                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ crypto-news │  │    n8n      │  │   backup    │         │
│  │  (daily)    │  │  (workflow) │  │  (6-hourly) │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│              ┌─────────────────────┐                        │
│              │   SHARED VOLUMES    │                        │
│              │ /app/data           │                        │
│              │ /app/config         │                        │
│              │ /app/scripts        │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Services Overview

| Service | Container | Schedule | Purpose |
|---------|-----------|----------|---------|
| **crypto-news** | `mech-crypto-news` | Daily 06:00 | Fetch crypto news, LLM score, send ≥8.0 to Telegram |
| **n8n** | `mech-n8n` | Continuous | Workflow automation (backup, alerts, etc.) |
| **backup** | `mech-backup` | Every 6 hours | Sync SQLite, n8n, Hermes data to OneDrive/R2 |

---

## 🔧 Daily Operations

### Morning Check (After 06:30)
```bash
# 1. Verify crypto news ran
docker compose -f infra/docker-compose.yml logs mech-crypto-news --tail=20

# 2. Check Telegram for news digest
# Should receive message ~06:10 with ≥8.0 scored articles

# 3. Quick health check
docker compose -f infra/docker-compose.yml ps
```

### Backup Verification (Every 6 hours: 00:00, 06:00, 12:00, 18:00)
```bash
# Check backup logs
docker compose -f infra/docker-compose.yml logs mech-backup --tail=30

# Verify files in cloud
rclone lsl onedrive:Backups/sqlite/ | tail -3
rclone lsl onedrive:Backups/n8n/ | tail -3
```

### n8n Workflow Monitoring
```bash
# Access n8n UI
# http://<VM-IP>:5678 (basic auth: admin / <password>)

# Check workflow executions
# Look for: Daily Backup to Cloud (every 6h)
```

---

## 🚨 Incident Response

### Alert: No Crypto News at 06:30
```bash
# 1. Check container logs
docker compose logs mech-crypto-news --tail=50

# 2. Common issues:
# - OpenRouter API key invalid/expired → Update .env
# - Telegram bot token invalid → Update .env
# - Network timeout → Check internet, retry manually
# - No new articles ≥8.0 → Normal, check DB

# 3. Manual run
docker compose run --rm crypto-news python scripts/crypto_news_scorer.py
```

### Alert: Backup Failed (Telegram from n8n)
```bash
# 1. Check backup container logs
docker compose logs mech-backup --tail=50

# 2. Common issues:
# - rclone remote not configured → rclone config
# - OneDrive token expired → rclone config onedrive (re-auth)
# - R2 credentials invalid → Update .env
# - Disk full → df -h, clean up

# 3. Manual backup
docker compose run --rm backup python scripts/backup.py
```

### Alert: Container Down (Health Check)
```bash
# 1. Check status
docker compose ps

# 2. Restart specific service
docker compose restart mech-crypto-news
docker compose restart mech-n8n
docker compose restart mech-backup

# 3. If persistent, check logs
docker compose logs <service> --tail=100

# 4. Full restart
docker compose down && docker compose up -d --build
```

### Alert: Telegram Bot Not Responding
```bash
# 1. Test bot token
curl "https://api.telegram.org/bot${TG_BOT_TOKEN}/getMe"

# 2. Test send
curl -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TG_CHAT_ID}" -d text="Test from runbook"

# 3. If 401/403: Bot token revoked → Get new from @BotFather
# 4. If 400: Chat ID wrong → Verify TG_CHAT_ID
```

---

## 🔄 Routine Maintenance

### Weekly (Sunday)
```bash
# 1. Verify weekly repo backup ran
rclone lsl onedrive:Backups/repo/ | tail -3

# 2. Clean old Docker images
docker image prune -f

# 3. Check disk space
df -h /

# 4. Review Telegram alerts for the week
# Search "⚠️" or "❌" in chat
```

### Monthly
```bash
# 1. Rotate secrets (if policy requires)
# - OpenRouter API key
# - Telegram bot token (if compromised)
# - n8n encryption key
# - R2 credentials

# 2. Full migration drill
# Follow docs/MIGRATION.md on test VM

# 3. Update dependencies
# - Docker base images
# - Python packages (requirements.txt)
# - n8n version

# 4. Review and archive old logs
find /app/data -name "*.log" -mtime +30 -delete
```

### Quarterly
```bash
# 1. Full disaster recovery test
# - Provision new VM
# - Follow MIGRATION.md
# - Time it (target < 30 min)

# 2. Review and update runbooks
# - This document
# - MIGRATION.md
# - Cronjob definitions

# 3. Audit secrets access
# - Who has 1Password/Bitwarden access?
# - Revoke unused tokens
```

---

## 🛠️ Common Commands Reference

### Docker Compose
```bash
# Start all services
docker compose -f infra/docker-compose.yml up -d

# Start specific profile
docker compose -f infra/docker-compose.yml --profile crypto up -d
docker compose -f infra/docker-compose.yml --profile n8n up -d
docker compose -f infra/docker-compose.yml --profile backup up -d

# Stop all
docker compose -f infra/docker-compose.yml down

# Rebuild and restart
docker compose -f infra/docker-compose.yml up -d --build

# View logs
docker compose -f infra/docker-compose.yml logs -f [service]

# Execute command in container
docker compose -f infra/docker-compose.yml exec mech-n8n bash
docker compose -f infra/docker-compose.yml run --rm crypto-news python scripts/crypto_news_scorer.py
```

### rclone
```bash
# List remotes
rclone listremotes

# Test remote
rclone lsd onedrive:
rclone lsd r2:

# Sync (one-way, source → dest)
rclone copy /src onedrive:dest --progress

# Sync (bidirectional, careful!)
rclone bisync /src onedrive:dest --progress

# Check config
rclone config show
```

### Database (SQLite)
```bash
# Query articles
sqlite3 data/sqlite/news.db "SELECT COUNT(*) FROM articles;"
sqlite3 data/sqlite/news.db "SELECT source, title, final_score FROM articles ORDER BY final_score DESC LIMIT 10;"

# Export to CSV
sqlite3 -header -csv data/sqlite/news.db "SELECT * FROM articles WHERE final_score >= 8;" > high_score_articles.csv
```

### Telegram Bot
```bash
# Get bot info
curl "https://api.telegram.org/bot${TG_BOT_TOKEN}/getMe"

# Get updates (see chat IDs)
curl "https://api.telegram.org/bot${TG_BOT_TOKEN}/getUpdates"

# Send message
curl -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TG_CHAT_ID}" \
  -d text="Message from runbook" \
  -d parse_mode="Markdown"
```

---

## 📞 Escalation Path

| Severity | Response Time | Action |
|----------|---------------|--------|
| **P1 - Critical** (No news, backup failed 2x) | 15 min | Manual run, notify via Telegram, investigate root cause |
| **P2 - High** (Container down, n8n workflow failed) | 1 hour | Restart service, check logs, fix config |
| **P3 - Medium** (Disk space low, slow performance) | 4 hours | Clean up, investigate growth |
| **P4 - Low** (Minor log warnings, cosmetic) | Next maintenance | Log, schedule fix |

---

## 📝 Change Log

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-08-12 | 1.0 | Initial runbook created | System |

---

**Next Review:** 2026-09-12  
**Owner:** System Administrator  
**Location:** `~/mech-automation/docs/RUNBOOK.md`