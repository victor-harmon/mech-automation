#!/usr/bin/env python3
"""
Backup script - runs every 6 hours via cron
Backs up SQLite DBs, n8n data, Hermes data to OneDrive and R2
"""
import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/data/backup.log')
    ]
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path('/app/data')
CONFIG_DIR = Path('/app/config')

# rclone remotes from env
ONEDRIVE_REMOTE = os.getenv('RCLONE_ONEDRIVE_REMOTE', 'onedrive')
R2_REMOTE = os.getenv('RCLONE_R2_REMOTE', 'r2')
R2_BUCKET = os.getenv('R2_BUCKET', '')

def run_rclone(src: str, dst: str, desc: str) -> bool:
    """Run rclone copy with error handling"""
    try:
        logger.info(f"Backing up {desc}: {src} -> {dst}")
        result = subprocess.run([
            'rclone', 'copy', src, dst,
            '--progress',
            '--transfers', '4',
            '--checkers', '8',
            '--stats', '30s'
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            logger.info(f"✅ {desc} backup successful")
            return True
        else:
            logger.error(f"❌ {desc} backup failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {desc} backup timeout")
        return False
    except Exception as e:
        logger.error(f"❌ {desc} backup error: {e}")
        return False

def main():
    logger.info("=" * 60)
    logger.info(f"BACKUP STARTED - {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    success_count = 0
    total_count = 0
    
    # Backup targets
    targets = [
        # (source, onedrive_dest, r2_dest, description)
        (str(DATA_DIR / 'sqlite'), f'{ONEDRIVE_REMOTE}:Backups/sqlite', f'{R2_REMOTE}:{R2_BUCKET}/Backups/sqlite', 'SQLite DBs'),
        (str(Path.home() / '.n8n'), f'{ONEDRIVE_REMOTE}:Backups/n8n', f'{R2_REMOTE}:{R2_BUCKET}/Backups/n8n', 'n8n data'),
        (str(Path.home() / '.hermes'), f'{ONEDRIVE_REMOTE}:Backups/hermes', f'{R2_REMOTE}:{R2_BUCKET}/Backups/hermes', 'Hermes data'),
    ]
    
    for src, od_dest, r2_dest, desc in targets:
        total_count += 1
        src_path = Path(src)
        if not src_path.exists():
            logger.warning(f"⚠️ Source not found, skipping: {src}")
            continue
        
        # Backup to OneDrive
        if run_rclone(src, od_dest, f"{desc} → OneDrive"):
            success_count += 1
        
        # Backup to R2 (if configured)
        if R2_BUCKET:
            total_count += 1
            if run_rclone(src, r2_dest, f"{desc} → R2"):
                success_count += 1
    
    logger.info("=" * 60)
    logger.info(f"BACKUP COMPLETED - {success_count}/{total_count} successful")
    logger.info("=" * 60)
    
    # Exit code for cron monitoring
    sys.exit(0 if success_count == total_count else 1)

if __name__ == '__main__':
    main()