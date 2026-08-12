# Migration Runbook: VM Free → New VM (Windows/Linux)

**Target:** Complete migration in **< 15 minutes**  
**Last tested:** 2026-08-12  
**Version:** 2.0 (Simplified - No Docker Required)

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] **New VM ready** (Windows 10/11/Server or Linux, 4GB+ RAM, 50GB+ disk)
- [ ] **Git installed** (`git --version`)
- [ ] **Python 3.11+ installed** (`python --version`)
- [ ] **GitHub CLI optional** (`gh auth login`) or use HTTPS clone
- [ ] **Secrets manager access** (1Password CLI, Bitwarden CLI, or manual)

---

## 🚀 Step-by-Step Migration (Target: < 15 min)

### 1. Clone Repository (1 min)
```bash
# HTTPS (works everywhere)
git clone https://github.com/timgarner111/vps-backups.git ~/mech-automation
cd ~/mech-automation

# OR with GitHub CLI (if authenticated)
# gh repo clone timgarner111/vps-backups ~/mech-automation
cd ~/vps-backups
git status  # Should be clean
```

### 2. Restore Secrets (2 min)

**Option A: 1Password (Recommended)**
```bash
# Install 1Password CLI if needed
# op inject -i config/.env.example -o config/.env

# Or manual export:
export OPENROUTER_API_KEY=$(op read "op://Private/OpenRouter_API_Key/credential")
export TG_BOT_TOKEN=$(op read "op://Private/TG_Bot_Token/credential")
export TG_CHAT_ID=$(op read "op://Private/TG_Chat_ID/credential")
export N8N_ENCRYPTION_KEY=$(op read "op://Private/N8N_Encryption_Key/credential")
export N8N_BASIC_AUTH_PASSWORD=$(op read "op://Private/N8N_Password/credential")
export R2_ACCESS_KEY_ID=$(op read "op://Private/R2_Access_Key/credential")
export R2_SECRET_ACCESS_KEY=$(op read "op://Private/R2_Secret_Key/credential")
export R2_ACCOUNT_ID=$(op read "op://Private/R2_Account_ID/credential")

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

**Required secrets to fill:**
| Variable | Required | Source |
|----------|----------|--------|
| `OPENROUTER_API_KEY` | ✅ Yes | OpenRouter dashboard |
| `TG_BOT_TOKEN` | ✅ Yes | @BotFather |
| `TG_CHAT_ID` | ✅ Yes | @userinfobot |
| `N8N_ENCRYPTION_KEY` | ✅ If using n8n | `openssl rand -hex 32` |
| `N8N_BASIC_AUTH_PASSWORD` | ✅ If using n8n | Your choice |
| `R2_ACCESS_KEY_ID` | Optional | Cloudflare R2 |
| `R2_SECRET_ACCESS_KEY` | Optional | Cloudflare R2 |
| `R2_ACCOUNT_ID` | Optional | Cloudflare R2 |

### 3. Install Dependencies (2 min)
```bash
# Windows
python -m pip install -r requirements.txt

# Linux
pip3 install -r requirements.txt
```

### 4. Setup Scheduler (2 min)

**Windows (Task Scheduler):**
```powershell
# Crypto Morning News - Daily 6:00 AM
schtasks /create /tn "CryptoMorningNews" /tr "cmd.exe /c cd /d C:\Users\%USERNAME%\vps-backups && python scripts\crypto_news_scorer.py >> C:\Users\%USERNAME%\crypto_news_data\crypto_news_cron.log 2>&1" /sc daily /st 06:00 /ru "%USERNAME%" /rl highest /f

# Daily Git Backup - 2:00 AM
schtasks /create /tn "DailyGitBackup" /tr "cmd.exe /c cd /d C:\Users\%USERNAME%\vps-backups && git add -A && git commit -m \"auto: daily backup %date% %time%\" && git push origin main >> C:\Users\%USERNAME%\vps-backups\git_backup.log 2>&1" /sc daily /st 02:00 /ru "%USERNAME%" /rl highest /f
```

**Linux (cron):**
```bash
crontab -l > /tmp/cron_backup_$(date +%s)
cat >> /tmp/cron_new << 'EOF'
# Crypto Morning News - Daily 6:00 AM
0 6 * * * cd ~/vps-backups && python scripts/crypto_news_scorer.py >> ~/crypto_news_data/crypto_news_cron.log 2>&1

# Daily Git Backup - 2:00 AM
0 2 * * * cd ~/vps-backups && git add -A && git commit -m "auto: daily backup $(date)" && git push origin main >> ~/vps-backups/git_backup.log 2>&1
EOF
crontab /tmp/cron_new
crontab -l
```

### 5. Test End-to-End (3 min)
```bash
# Test crypto news bot
python scripts/crypto_news_scorer.py

# Verify Telegram receives message
# Check log
cat ~/crypto_news_data/crypto_news_cron.log

# Test git backup
git add -A && git commit -m "test: migration verify" && git push origin main

# Verify GitHub received commit
```

---

## ✅ Post-Migration Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| Python script runs | `python scripts/crypto_news_scorer.py` | No errors, Telegram msg |
| Git push works | `git push origin main` | Commit on GitHub |
| Telegram bot works | Test message | Received in chat |
| Scheduler installed | `schtasks /query /tn "CryptoMorningNews"` (Win) or `crontab -l` (Linux) | Shows tasks |
| Git push works | `git push origin main` | Commit on GitHub |
| Secrets loaded | `python -c "import os; print(os.getenv('OPENROUTER_API_KEY')[:10])"` | Shows key prefix |

---

## 🔄 Rollback Plan (if migration fails)

```bash
# 1. New VM - just delete folder and retry
rm -rf ~/vps-backups  # or ~/mech-automation

# 2. Old VM still alive - continue using it
#    No action needed

# 3. Emergency: Run on any machine with Python + Git
git clone https://github.com/timgarner111/vps-backups.git
cd vps-backups
cp config/.env.example config/.env
# Fill secrets manually
python scripts/crypto_news_scorer.py
```

---

## 📞 Emergency Contacts & Resources

| Resource | URL/Command |
|----------|-------------|
| GitHub Repo | `https://github.com/timgarner111/vps-backups` |
| GitHub Actions | `https://github.com/timgarner111/vps-backups/actions` |
| OpenRouter | `https://openrouter.ai/keys` |
| Telegram Bot API | `https://core.telegram.org/bots/api` |
| Cloudflare R2 | `https://dash.cloudflare.com` |
| Windows Task Scheduler | `taskschd.msc` |

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

---

## 📝 Architecture Notes (v2.0 - Simplified)

**No Docker Required** - Runs natively on Python 3.11+
- `scripts/crypto_news_scorer.py` - Daily crypto news bot
- `scripts/*.py` - Mechanical automation tools (future)
- Windows Task Scheduler / Linux cron for scheduling
- GitHub for code backup & version control
- GitHub Secrets for CI/CD (optional)
- GitHub Actions for lint/test/build (optional)

**Runtime Data (Accept Recreation):**
- SQLite DB (news articles) - recreated daily
- n8n workflows - export/import manually if needed
- Hermes memory - rebuilt from scratch

**Code is the Source of Truth** - Everything in GitHub.