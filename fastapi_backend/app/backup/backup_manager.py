
import shutil, datetime, os

# Database file path in database/ folder
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database")
DB_FILE = os.path.join(DB_DIR, "broker.db")
BACKUP_DIR = "backups"

def backup(kind="daily"):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target = f"{BACKUP_DIR}/{kind}/{DB_FILE}_{ts}.sqlite"
    if os.path.exists(DB_FILE):
        shutil.copy(DB_FILE, target)
