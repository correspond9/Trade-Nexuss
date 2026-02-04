
import shutil
import os

def restore(path):
    # Restore to database/ folder
    db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database")
    os.makedirs(db_dir, exist_ok=True)
    target_path = os.path.join(db_dir, "broker.db")
    shutil.copy(path, target_path)
