from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.storage.migrations import init_db
from app.storage.auto_credentials import auto_load_credentials
from app.storage.settings_manager import restore_settings_to_database
from app.rest.credentials import router as cred_router
from app.rest.settings import router as settings_router
from app.rest.ws import router as ws_router
from app.rest.market_api_v2 import router as market_v2_router
from app.lifecycle.hooks import on_start, on_stop
from app.market.instrument_master.registry import load_instruments
from app.market.atm_engine import get_atm_engine
from app.market.subscription_manager import get_subscription_manager
from app.market.ws_manager import get_ws_manager
from app.services.authoritative_option_chain_service import authoritative_option_chain_service
from app.market.closing_prices import get_closing_prices
from app.schedulers.expiry_refresh_scheduler import get_expiry_scheduler
from app.schedulers.market_aware_cache_scheduler import get_market_aware_cache_scheduler

app = FastAPI(title="Data Server Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    print("[STARTUP] Initializing backend...")
    init_db()
    
    # Restore locked settings from previous session
    print("[STARTUP] Checking for saved settings...")
    restore_settings_to_database()
    
    # Auto-load credentials from environment variables (or use restored ones)
    print("[STARTUP] Auto-loading credentials from environment...")
    auto_load_credentials()
    
    # Load instrument registry
    print("[STARTUP] Loading instrument master...")
    load_instruments()
    
    # Initialize authoritative option chain service first
    print("[STARTUP] Initializing authoritative option chain service...")
    await authoritative_option_chain_service.initialize()
    
    # Start daily expiry refresh scheduler
    print("[STARTUP] Starting daily expiry refresh scheduler (runs at 4 PM daily)...")
    try:
        scheduler = get_expiry_scheduler()
        await scheduler.start()
        print("[STARTUP] ✅ Expiry scheduler started")
    except Exception as e:
        print(f"[STARTUP] ⚠️ Failed to start expiry scheduler: {e}")
    
    # Initialize managers
    print("[STARTUP] Initializing managers...")
    atm_engine = get_atm_engine()
    sub_mgr = get_subscription_manager()
    ws_mgr = get_ws_manager()
    
    # ========== MARKET-AWARE CACHE POPULATION ==========
    # The new strategy: detect market hours and automatically use LIVE or CLOSING prices
    print("[STARTUP] Checking market status and populating cache with appropriate data source...")
    print("[STARTUP]    • If markets OPEN: Load LIVE prices from DhanHQ API")
    print("[STARTUP]    • If markets CLOSED: Load CLOSING prices from closing_prices.py")
    print("[STARTUP]    • System will AUTO-SWITCH when market status changes")
    
    cache_populated = await authoritative_option_chain_service.populate_cache_with_market_aware_data()
    
    if not cache_populated:
        print("[STARTUP] ❌ FATAL: Market-aware cache population failed!")
        raise RuntimeError("Option chain cache population failed - cannot start backend")
    
    stats = authoritative_option_chain_service.get_cache_statistics()
    print(f"[STARTUP] ✅ Cache populated successfully:")
    print(f"[STARTUP]    • Underlyings: {stats['total_underlyings']}")
    print(f"[STARTUP]    • Expiries: {stats['total_expiries']}")
    print(f"[STARTUP]    • Strikes: {stats['total_strikes']}")
    print(f"[STARTUP]    • Tokens: {stats['total_tokens']}")
    
    # Display which data source is being used
    cache_sources = authoritative_option_chain_service.cache_source
    if cache_sources:
        print("[STARTUP] Data sources in use:")
        for underlying, source in sorted(cache_sources.items()):
            print(f"[STARTUP]    • {underlying}: {source}")
    
    print("[STARTUP] Starting market-aware cache refresh scheduler...")
    try:
        market_scheduler = get_market_aware_cache_scheduler()
        await market_scheduler.start()
        print("[STARTUP] ✅ Market-aware cache scheduler started")
    except Exception as e:
        print(f"[STARTUP] ⚠️ Failed to start market-aware cache scheduler: {e}")
    
    print("[STARTUP] Starting lifecycle hooks...")
    on_start()
    
    print("[STARTUP] Backend ready!")

@app.on_event("shutdown")
async def shutdown():
    print("[SHUTDOWN] Stopping schedulers...")
    
    try:
        scheduler = get_expiry_scheduler()
        await scheduler.stop()
        print("[SHUTDOWN] ✅ Expiry scheduler stopped")
    except Exception as e:
        print(f"[SHUTDOWN] ⚠️ Error stopping expiry scheduler: {e}")
    
    try:
        market_scheduler = get_market_aware_cache_scheduler()
        await market_scheduler.stop()
        print("[SHUTDOWN] ✅ Market-aware cache scheduler stopped")
    except Exception as e:
        print(f"[SHUTDOWN] ⚠️ Error stopping market-aware cache scheduler: {e}")
    
    on_stop()

app.include_router(cred_router, prefix="/api/v2", tags=["credentials"])
app.include_router(settings_router, prefix="/api/v2", tags=["settings"])
app.include_router(ws_router)
app.include_router(market_v2_router)

# Serve static files (JS, CSS if any)
import os
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ✅ Explicit UI route
@app.get("/ui")
def ui():
    return FileResponse("static/index.html")

@app.get("/")
def root():
    return {"status": "running"}

@app.get("/health")
def health():
    """Health check endpoint"""
    from app.market.subscription_manager import get_subscription_manager
    from app.market.ws_manager import get_ws_manager
    
    sub_mgr = get_subscription_manager()
    ws_mgr = get_ws_manager()
    
    return {
        "status": "healthy",
        "subscriptions": sub_mgr.get_active_count(),
        "websocket_status": ws_mgr.get_status()
    }

