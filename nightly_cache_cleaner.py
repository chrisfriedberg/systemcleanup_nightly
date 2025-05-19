import os
import shutil
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler

# ==== CONFIG ====
LOG_PATH = os.path.expanduser("~/Downloads/NightlyCleanupLog.txt")
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 3

MAX_FILE_AGE_DAYS = 3
NOW = datetime.now()

# Add any other AI/model/temp folders here if needed
TARGET_FOLDERS = [
    os.environ.get("TEMP"),
    os.path.expandvars(r"%USERPROFILE%\AppData\Local\Temp"),
]

EXCLUDE_EXTENSIONS = ['.log', '.bak', '.tmp']
EXCLUDE_KEYWORDS = ['important', 'do_not_delete']

# === LOGGING SETUP ===
def setup_logging():
    logger = logging.getLogger('cleanup')
    logger.setLevel(logging.INFO)
    
    # Create rotating file handler
    handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

logger = setup_logging()

# === STATISTICS ===
class CleanupStats:
    def __init__(self):
        self.files_deleted = 0
        self.folders_deleted = 0
        self.files_skipped = 0
        self.folders_skipped = 0
        self.errors = 0
        self.total_size_cleaned = 0

stats = CleanupStats()

# === HELPERS ===
def is_old_enough(path):
    try:
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        return (NOW - mtime) > timedelta(days=MAX_FILE_AGE_DAYS)
    except Exception as e:
        logger.error(f"Error checking file age for {path}: {e}")
        return False

def get_file_size(path):
    try:
        return os.path.getsize(path)
    except Exception:
        return 0

def safe_delete_file(file_path):
    if not is_old_enough(file_path):
        stats.files_skipped += 1
        return
    if any(file_path.lower().endswith(ext) for ext in EXCLUDE_EXTENSIONS):
        stats.files_skipped += 1
        logger.debug(f"Skipped file (excluded extension): {file_path}")
        return
    if any(keyword in file_path.lower() for keyword in EXCLUDE_KEYWORDS):
        stats.files_skipped += 1
        logger.debug(f"Skipped file (excluded keyword): {file_path}")
        return
    try:
        size = get_file_size(file_path)
        os.remove(file_path)
        stats.files_deleted += 1
        stats.total_size_cleaned += size
        logger.info(f"Deleted file: {file_path} ({size/1024:.2f} KB)")
    except Exception as e:
        stats.errors += 1
        logger.error(f"Failed to delete file: {file_path} - {e}")

def safe_delete_folder(folder_path):
    if not is_old_enough(folder_path):
        stats.folders_skipped += 1
        return
    try:
        size = sum(get_file_size(os.path.join(dirpath, filename))
                  for dirpath, _, filenames in os.walk(folder_path)
                  for filename in filenames)
        shutil.rmtree(folder_path)
        stats.folders_deleted += 1
        stats.total_size_cleaned += size
        logger.info(f"Deleted folder: {folder_path} ({size/1024:.2f} KB)")
    except Exception as e:
        stats.errors += 1
        logger.error(f"Failed to delete folder: {folder_path} - {e}")

def log_summary():
    logger.info("=== Cleanup Summary ===")
    logger.info(f"Files deleted: {stats.files_deleted}")
    logger.info(f"Folders deleted: {stats.folders_deleted}")
    logger.info(f"Files skipped: {stats.files_skipped}")
    logger.info(f"Folders skipped: {stats.folders_skipped}")
    logger.info(f"Total space cleaned: {stats.total_size_cleaned/1024/1024:.2f} MB")
    logger.info(f"Errors encountered: {stats.errors}")
    logger.info("=====================")

# === MAIN CLEANUP ===
logger.info("\n\n========== NEW CLEANUP RUN ==========\n")
logger.info("=== Nightly Cleanup Started ===")

for folder in TARGET_FOLDERS:
    if folder and os.path.exists(folder):
        logger.info(f"Processing folder: {folder}")
        for root, dirs, files in os.walk(folder, topdown=False):
            for file in files:
                safe_delete_file(os.path.join(root, file))
            for dir in dirs:
                full_path = os.path.join(root, dir)
                if dir == "__pycache__":
                    safe_delete_folder(full_path)

log_summary()
logger.info("=== Nightly Cleanup Complete ===\n")
