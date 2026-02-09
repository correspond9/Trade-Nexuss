
Delete everything.

Paste this:

```python
from fastapi import FastAPI
import logging

# routers
from app.rest.market_api_v2 import router as market_router

# DB modules (keep imports, but do NOT run immediately)
from app.storage.migrations import init_db
from app.storage.auto_credentials import auto_load_credentials
from app.storage.settings_manager import restore_settings_to_database

app = FastAPI()

logger = logging.getLogger(__name__)


# -------------------------------------------------------
# SAFE STARTUP (DB WILL NOT BLOCK APP BOOT)
# -------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting database initialization...")

        # Run DB setup safely
        init_db()
        auto_load_credentials()
        restore_settings_to_database()

        logger.info("Database initialization completed.")

    except Exception as e:
        logger.error(f"Database startup skipped: {e}")


# -------------------------------------------------------
# ROUTERS
# -------------------------------------------------------

app.include_router(market_router)


# -------------------------------------------------------
# BASIC HEALTH CHECK
# -------------------------------------------------------

@app.get("/")
def root():
    return {"status": "backend running"}
