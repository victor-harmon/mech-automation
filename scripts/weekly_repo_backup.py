#!/usr/bin/env python3
"""
Weekly repository backup - runs Sunday 3:00 AM
Creates full repo archive and uploads to cloud
"""
import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

ONEDRIVE_REMOTE = os.getenv('RCLONE_ONEDRIVE_REMOTE', 'onedrive')
R2_REMOTE = os.getenv('RCLONE_R2_REMOTE', 'r2')
R2_BUCKET = os.getenv('R2_BUCKET', '')

REPO_DIR = Path('/app').parent  # /home/appuser -> /app -> repo root
BACKUP_DIR = Path('/tmp')

def run_cmd(cmd: list, desc: str) -> bool:
    try:
        logger.info(f"{desc}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            logger.info(f"✅ {desc} OK")
            return True
        else:
            logger.error(f"❌ {desc} failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ {desc} error: {e}")
        return False

def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_name = f"mech-automation_{timestamp}.tar.gz"
    archive_path = BACKUP_DIR / archive_name
    
    logger.info(f"Starting weekly repo backup: {archive_name}")
    
    # Create archive (exclude .git, __pycache__, .env, data)
    if not run_cmd([
        'tar', 'czf', str(archive_path),
        '--exclude=.git',
        '--exclude=__pycache__',
        '--exclude=*.pyc',
        '--exclude=.env',
        '--exclude=.env.*',
        '--exclude=data/',
        '--exclude=*.db',
        '--exclude=*.sqlite*',
        '--exclude=.n8n/',
        '--exclude=node_modules/',
        '--exclude=.docker/',
        '-C', str(REPO_DIR), '.'
    ], f"Creating archive {archive_name}"):
        sys.exit(1)
    
    # Verify archive
    if not archive_path.exists():
        logger.error("Archive not created")
        sys.exit(1)
    
    size_mb = archive_path.stat().st_size / (1024 * 1024)
    logger.info(f"Archive created: {archive_name} ({size_mb:.1f} MB)")
    
    # Upload to OneDrive
    if not run_cmd([
        'rclone', 'copy', str(archive_path),
        f'onedrive:Backups/repo/',
        '--progress', '--stats', '30s'
    ], "Upload to OneDrive"):
        sys.exit(1)
    
    # Upload to R2 (if configured)
    r2_bucket = os.getenv('R2_BUCKET', '')
    if r2_bucket:
        if not run_cmd([
            'rclone', 'copy', str(archive_path),
            f'r2:{r2_bucket}/Backups/repo/',
            '--progress', '--stats', '30s'
        ], "Upload to R2"):
            sys.exit(1)
    
    # Cleanup local archive
    archive_path.unlink(missing_ok=True)
    logger.info("Weekly repo backup completed successfully")

if __name__ == '__main__':
    main()