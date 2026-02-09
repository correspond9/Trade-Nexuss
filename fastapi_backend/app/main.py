# ==================================================
# FastAPI Application Entry Point
# ==================================================

from fastapi import FastAPI
import logging

# Routers
from app.rest.market_api_v2 import router as market_router

# Optional DB utilities (safe startup)
from app.storage.migrations import init_db
from app.storage.auto_credentials import auto_load_credentials
from app.storage.settings_manager import restore_settings_to_database

# --------------------------------------------------
# App Initialization
# --------------------------------------------------

app = FastAPI(
    title="Trading Nexus API",
    version="1.0.0"
)

logger = logging.getLogger(__name__)

# --------------------------------------------------
# Safe Startup Hook (DB must NOT block boot)
# --------------------------------------------------

@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting optional database initialization...")
        init_db()
        auto_load_credentials()
        restore_settings_to_database()
        logger.info("Database initialization completed.")
    except Exception as e:
        logger.error(f"Database startup skipped: {e}")

# --------------------------------------------------
# Routes
# --------------------------------------------------

app.include_router(market_router)

# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/")
def root():
    return {"status": "backend running"}
