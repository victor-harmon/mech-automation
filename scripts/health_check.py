#!/usr/bin/env python3
"""
Health check script - runs every 15 minutes via cron
Verifies all services running, sends alert if down
"""
import os
import sys
import subprocess
import requests
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

def send_telegram(message: str) -> bool:
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=payload, timeout=10)
        return resp.ok
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False

def check_docker_containers() -> tuple[bool, str]:
    """Check if all expected containers are running"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}:{{.Status}}'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False, f"Docker command failed: {result.stderr}"
        
        containers = result.stdout.strip().split('\n')
        expected = ['mech-crypto-news', 'mech-n8n', 'mech-backup']
        running = [c.split(':')[0] for c in containers if 'Up' in c]
        missing = [e for e in expected if e not in running]
        
        if missing:
            return False, f"Missing containers: {', '.join(missing)}"
        return True, f"All {len(expected)} containers running"
    except Exception as e:
        return False, f"Docker check error: {e}"

def check_n8n_health() -> tuple[bool, str]:
    """Check n8n API health"""
    try:
        resp = requests.get('http://localhost:5678/healthz', timeout=10)
        if resp.status_code == 200:
            return True, "n8n healthy"
        return False, f"n8n unhealthy: HTTP {resp.status_code}"
    except Exception as e:
        return False, f"n8n check error: {e}"

def check_disk_space() -> tuple[bool, str]:
    """Check disk space > 10% free"""
    try:
        stat = os.statvfs('/')
        free_pct = (stat.f_bavail * stat.f_frsize) / (stat.f_blocks * stat.f_frsize) * 100
        if free_pct < 10:
            return False, f"Low disk space: {free_pct:.1f}% free"
        return True, f"Disk OK: {free_pct:.1f}% free"
    except Exception as e:
        return False, f"Disk check error: {e}"

def check_rclone_remotes() -> tuple[bool, str]:
    """Check rclone remotes configured"""
    try:
        result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return False, "rclone listremotes failed"
        remotes = result.stdout.strip().split('\n')
        required = ['onedrive:', 'r2:']
        missing = [r for r in required if r not in remotes]
        if missing:
            return False, f"Missing rclone remotes: {', '.join(missing)}"
        return True, f"rclone remotes OK: {', '.join(remotes)}"
    except Exception as e:
        return False, f"rclone check error: {e}"

def main():
    checks = [
        ("Docker Containers", check_docker_containers),
        ("n8n Health", check_n8n_health),
        ("Disk Space", check_disk_space),
        ("rclone Remotes", check_rclone_remotes),
    ]
    
    results = []
    all_ok = True
    
    for name, check_fn in checks:
        ok, msg = check_fn()
        status = "✅" if ok else "❌"
        results.append(f"{status} {name}: {msg}")
        if not ok:
            all_ok = False
    
    # Summary
    summary = f"🏥 Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n" + "\n".join(results)
    logger.info(summary)
    
    # Alert if any failed
    if not all_ok:
        alert_msg = f"⚠️ *HEALTH ALERT*\n{summary}"
        send_telegram(alert_msg)
        logger.warning("Health check FAILED - alert sent")
        sys.exit(1)
    else:
        logger.info("All health checks PASSED")
        sys.exit(0)

if __name__ == '__main__':
    main()