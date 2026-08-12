# mech-automation

**Portable automation infrastructure for Mechanical Engineering workflows**

> **Designed for migration:** Run on any VM, backup to cloud, restore in <30 min.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DOCKER COMPOSE                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ crypto-news │  │    n8n      │  │   backup    │         │
│  │  (daily)    │  │  (workflow) │  │  (6-hourly) │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
         │                │                │
         └────────────────┼────────────────┘
                          ▼
              ┌─────────────────────┐
              │   CLOUD BACKUP      │
              │ OneDrive + R2 (S3)  │
              └─────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Docker + Docker Compose
- GitHub CLI (`gh`)
- rclone (configured with OneDrive + R2)
- Secrets manager (1Password/Bitwarden) or manual `.env`

### 1. Clone & Configure
```bash
gh repo clone <user>/mech-automation ~/mech-automation
cd ~/mech-automation

# Copy and fill secrets
cp config/.env.example config/.env
# Edit config/.env with your values
```

### 2. Start Services
```bash
# All services
docker compose -f infra/docker-compose.yml up -d --build

# Or specific profiles
docker compose -f infra/docker-compose.yml --profile crypto up -d
docker compose -f infra/docker-compose.yml --profile n8n up -d
docker compose -f infra/docker-compose.yml --profile backup up -d
```

### 3. Verify
```bash
# Check containers
docker compose -f infra/docker-compose.yml ps

# Test crypto news (manual)
docker compose -f infra/docker-compose.yml run --rm crypto-news python scripts/crypto_news_scorer.py

# Test backup
docker compose -f infra/docker-compose.yml run --rm backup python scripts/backup.py
```

---

## 📦 Services

| Service | Schedule | Description |
|---------|----------|-------------|
| **crypto-news** | Daily 06:00 | Fetch crypto news → LLM score → Send ≥8.0 to Telegram |
| **n8n** | Continuous | Workflow automation (backup, alerts, etc.) |
| **backup** | Every 6 hours | Sync SQLite, n8n, Hermes data to OneDrive + R2 |

---

## 🔧 Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/crypto_news_scorer.py` | Main crypto news pipeline |
| `scripts/backup.py` | Multi-cloud backup (OneDrive + R2) |
| `scripts/health_check.py` | System health monitoring |
| `scripts/weekly_repo_backup.py` | Weekly repo archive to cloud |

---

## 📅 Cronjobs (Defined in `cron/jobs.yaml`)

| Job | Schedule | Script |
|-----|----------|--------|
| crypto-morning-news | `0 6 * * *` | `scripts/crypto_news_scorer.py` |
| daily-backup | `0 */6 * * *` | `scripts/backup.py` |
| weekly-repo-backup | `0 3 * * 0` | `scripts/weekly_repo_backup.py` |
| health-check | `*/15 * * * *` | `scripts/health_check.py` |

---

## ☁️ Backup Strategy (3-2-1)

| Data | Primary | Secondary | Tertiary | Frequency |
|------|---------|-----------|----------|-----------|
| Code/Config | GitHub | GitHub Mirror | Local | Every commit |
| SQLite DBs | OneDrive | R2 | Local | Every 6 hours |
| n8n Data | OneDrive | R2 | Local | Every 6 hours |
| Hermes Data | OneDrive | R2 | Local | Every 6 hours |
| Product Files | GitHub LFS | R2 | Local | Per release |

---

## 🔄 Migration (Target: <30 min)

```bash
# 1. New VM: Install Docker, gh, rclone
# 2. Clone repo
gh repo clone <user>/mech-automation ~/mech-automation
cd ~/mech-automation

# 3. Restore secrets
cp config/.env.example config/.env
# Fill secrets (1Password/Bitwarden/manual)

# 4. Restore data
rclone copy onedrive:Backups/sqlite/ ./data/sqlite/ --progress
rclone copy onedrive:Backups/n8n/ ./data/n8n/ --progress
rclone copy onedrive:Backups/hermes/ ~/.hermes/ --progress

# 5. Start
docker compose -f infra/docker-compose.yml up -d --build

# 6. Verify
docker compose ps
curl localhost:5678/healthz
```

See [`docs/MIGRATION.md`](docs/MIGRATION.md) for detailed runbook.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [`docs/MIGRATION.md`](docs/MIGRATION.md) | Step-by-step migration runbook |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | Daily operations & incident response |
| [`cron/jobs.yaml`](cron/jobs.yaml) | Cronjob definitions |

---

## 🔐 Secrets Management

**Never commit `.env` or secrets!**

Use secrets manager:
- **1Password CLI:** `op inject -i config/.env.example -o config/.env`
- **Bitwarden CLI:** `bw get password "Key_Name"`
- **Manual:** Copy `.env.example` → `.env` and fill

Required secrets:
- `OPENROUTER_API_KEY` - LLM scoring
- `TG_BOT_TOKEN` / `TG_CHAT_ID` - Telegram notifications
- `CRYPTOPANIC_TOKEN` - Crypto news aggregator (optional)
- `N8N_ENCRYPTION_KEY` - n8n workflow encryption
- `R2_BUCKET` - Cloudflare R2 bucket name

---

## 🧪 CI/CD Pipeline

GitHub Actions (`.github/workflows/ci.yml`):
- **Lint & Test:** Ruff, Black, isort, pytest
- **Build:** Multi-stage Docker image → GHCR
- **Test Image:** Dry-run scripts
- **Migration Test:** Weekly fresh VM simulation
- **Deploy:** Manual trigger to VM

---

## 📁 Project Structure

```
mech-automation/
├── .github/workflows/     # CI/CD pipelines
├── infra/                 # Dockerfile, docker-compose.yml
├── scripts/               # Python automation scripts
├── n8n/workflows/         # n8n workflow exports (JSON)
├── cron/                  # Cronjob definitions (YAML)
├── config/                # .env.example, config templates
├── products/              # Digital product source files
├── docs/                  # MIGRATION.md, RUNBOOK.md
├── secrets/               # .gitignore only (no secrets!)
├── data/                  # Runtime data (gitignored)
└── .gitignore
```

---

## 🤝 Contributing

1. Fork → Feature branch → PR
2. Run lint: `ruff check scripts/ && black --check scripts/`
3. Test build: `docker compose -f infra/docker-compose.yml build`
4. Update docs if needed

---

## 📄 License

MIT License - Feel free to use for your own automation infrastructure.

---

**Built for portability. Runs anywhere Docker runs.**# CI/CD test - Wed, Aug 12, 2026 12:56:03 PM
