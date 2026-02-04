# 📁 Project Directory Structure

## Overview
Organized project structure with dedicated folders for documentation and database files.

---

## Root Directory Structure

```
data_server_backend/
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── admin/                    # Admin panel
│   ├── backup/                   # Backup/restore managers
│   ├── broadcaster/              # WebSocket broadcaster
│   ├── config/                   # Configuration
│   ├── dhan/                     # DhanHQ integration
│   ├── ems/                      # Execution engine
│   ├── ledger/                   # Margin & PnL
│   ├── lifecycle/                # App hooks
│   ├── logging/                  # Logger setup
│   ├── market/                   # Market data & subscriptions ⭐ NEW MODULES
│   │   ├── instrument_master/    # Instrument registry
│   │   ├── atm_engine.py         # ATM calculation
│   │   ├── subscription_manager.py
│   │   ├── watchlist_manager.py
│   │   └── ws_manager.py
│   ├── notifications/            # Notifications
│   ├── oms/                      # Order management
│   ├── rest/                     # REST API
│   │   ├── market_api_v2.py      # 16 endpoints ⭐
│   │   └── ...
│   ├── rms/                      # Risk management
│   ├── storage/                  # Database & models ✅ UPDATED
│   │   ├── db.py                 # Points to database/broker.db
│   │   ├── models.py             # +4 new tables
│   │   └── ...
│   ├── trading/                  # Trading engine
│   └── users/                    # User management
│
├── docs/                         # 📚 DOCUMENTATION FOLDER ⭐ NEW
│   ├── API_REFERENCE.md          # All 16 API endpoints
│   ├── ARCHITECTURE_DIAGRAM.md   # System architecture
│   ├── BACKEND_COMPLETE.md
│   ├── CHANGES.md
│   ├── CHECKLIST.md
│   ├── DHAN_MIGRATION.md
│   ├── FINAL_SUMMARY.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── INTEGRATION_CHECKLIST.md
│   ├── QUICK_REFERENCE.md
│   ├── QUICK_START.md
│   ├── README.md
│   ├── README_TESTING.md
│   ├── README_TWO_TIER_SYSTEM.md
│   ├── SETUP_COMPLETE.md
│   ├── TEST_GUIDE.md
│   └── TWO_TIER_SYSTEM_COMPLETE.md
│
├── vendor/                       # 🔗 EXTERNAL LIBRARIES ⭐ NEW
│   ├── README.md                 # Vendor libraries guide
│   └── dhanhq/                   # DhanHQ integration docs
│       ├── README.md             # Integration guide
│       ├── DHANHQ_USAGE.md       # Usage documentation
│       └── DHANHQ_DEPENDENCIES.md # Dependency matrix
│
├── database/                     # 💾 DATABASE FOLDER ⭐ NEW
│   └── broker.db                 # Main SQLite database (moved from root)
│
├── database-backups/             # Database backups (future)
│
├── backups/                      # Backup manager output
├── logs/                         # Application logs
├── node-market-data/             # Node.js market data
├── static/                       # Static files (frontend)
│
└── requirements.txt              # Python dependencies
```

---

## What Was Moved

### 📚 Documentation Files → `docs/`
| File | Purpose |
|------|---------|
| API_REFERENCE.md | All 16 REST endpoints with curl examples |
| ARCHITECTURE_DIAGRAM.md | System architecture & data flow diagrams |
| IMPLEMENTATION_SUMMARY.md | Implementation details |
| INTEGRATION_CHECKLIST.md | Phase 2-5 integration roadmap |
| TWO_TIER_SYSTEM_COMPLETE.md | Complete technical specification |
| QUICK_REFERENCE.md | Fast lookup card |
| README_TWO_TIER_SYSTEM.md | Executive summary |
| FINAL_SUMMARY.md | Project overview |
| Plus: BACKEND_COMPLETE.md, CHANGES.md, CHECKLIST.md, DHAN_MIGRATION.md, QUICK_START.md, README.md, README_TESTING.md, SETUP_COMPLETE.md, TEST_GUIDE.md |

**Total**: 17 documentation files organized in one place for easy reference

### 💾 Database Files → `database/`
| File | Purpose |
|------|---------|
| broker.db | Main SQLite database (all tables) |

**Future databases** should also be created here with relevant naming:
- `broker.db` - Production database
- `broker_test.db` - Testing database (future)
- `broker_backup_<date>.db` - Backup copies (future)

---

## Code Changes

### ✅ Updated Files (Database Path References)

#### 1. `app/storage/db.py`
**Before:**
```python
DATABASE_URL = "sqlite:///./broker.db"
```

**After:**
```python
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database")
os.makedirs(DB_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'broker.db').replace(chr(92), '/')}"
```

**Impact**: All SQLAlchemy sessions now use `database/broker.db` automatically

---

#### 2. `app/backup/backup_manager.py`
**Before:**
```python
DB_FILE = "broker.db"
```

**After:**
```python
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database")
DB_FILE = os.path.join(DB_DIR, "broker.db")
```

**Impact**: Backup function now reads from `database/broker.db`

---

#### 3. `app/backup/restore_manager.py`
**Before:**
```python
def restore(path):
    shutil.copy(path, "broker.db")
```

**After:**
```python
def restore(path):
    db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database")
    os.makedirs(db_dir, exist_ok=True)
    target_path = os.path.join(db_dir, "broker.db")
    shutil.copy(path, target_path)
```

**Impact**: Restore function now writes to `database/broker.db`

---

## ✅ Verification Results

```
✓ Database path: sqlite:///D:/4.PROJECTS/Broking_Terminal_V2/data_server_backend/database/broker.db
✓ Database connection successful
✓ DB_FILE: D:\4.PROJECTS\Broking_Terminal_V2\data_server_backend\database\broker.db
✓ BACKUP_DIR: backups
```

All code updates verified and working!

---

## Future Database Files

When creating new database files, place them in the `database/` folder:

```python
# Example: Create test database
import os
TEST_DB = os.path.join("database", "broker_test.db")
TEST_DB_URL = f"sqlite:///{TEST_DB.replace(chr(92), '/')}"
```

---

## Benefits of New Structure

✅ **Better Organization**: All docs in one place, all databases in one place  
✅ **Easier Maintenance**: Know exactly where to find documentation and database files  
✅ **Scalable**: Can add multiple database files (dev, test, prod) in `database/` folder  
✅ **Professional**: Follows industry standard project structure  
✅ **Git-friendly**: Easy to add `.gitignore` rules for database folder  

Example `.gitignore` entry:
```
database/*.db
database/*.sqlite
!database/.gitkeep
```

---

## Quick Commands

**Start backend:**
```bash
python -m uvicorn app.main:app --port 8000
```

**View documentation:**
```bash
# Open in VS Code
code docs/QUICK_REFERENCE.md
```

**Check database:**
```bash
sqlite3 database/broker.db ".tables"
```

---

**Status**: ✅ Project reorganization complete  
**Date**: February 3, 2026
