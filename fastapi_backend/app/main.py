import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from app.storage import db as storage_db

# import routers
from app.rest.market_api_v2 import router as market_router
from app.rest.credentials import router as credentials_router
from app.rest.auth import router as auth_router
from app.rest.settings import router as settings_router
from app.rest.ws import router as ws_router
from app.rest.mock_exchange import router as mock_exchange_router
from app.commodity_engine.commodity_rest import router as commodity_router
from app.trading.positions import router as positions_router
from app.trading.orders import router as orders_router
from app.routers.authoritative_option_chain import router as option_chain_router
from app.admin.admin_panel import router as admin_router

# Configure logging to ensure tracebacks appear in container logs
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("trading_nexus")
log.setLevel(logging.DEBUG)

app = FastAPI(
    title="Trading Nexus API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None
)

# Register lifecycle hooks (startup/shutdown) to initialize market caches and streams
from app.lifecycle import hooks as lifecycle_hooks

app.add_event_handler("startup", lifecycle_hooks.on_start)
app.add_event_handler("shutdown", lifecycle_hooks.on_stop)

# CORS: restrict to known frontend origins to allow credentials safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tradingnexus.pro",
        "https://www.tradingnexus.pro",
        "https://app.tradingnexus.pro",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base routes
@app.get("/")
def root():
    return {"message": "Trading Nexus API running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/deep")
def health_deep():
    """Run deeper checks (DB connectivity, later: Redis, WebSocket manager).

    Returns 200 when all checks pass, 500 when any check fails.
    """
    results = {"status": "ok", "checks": {}}
    # DB check
    try:
        with storage_db.engine.connect() as conn:
            conn.execute("SELECT 1")
        results["checks"]["database"] = {"status": "ok"}
    except Exception as e:
        tb = traceback.format_exc()
        log.error("Deep health: DB check failed:\n%s", tb)
        results["checks"]["database"] = {"status": "error", "error": str(e)}
        results["status"] = "fail"

    status_code = 200 if results["status"] == "ok" else 500
    return JSONResponse(status_code=status_code, content=results)


@app.get("/test")
def test():
    return {"message": "test route active"}

@app.get("/docs", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(url="/api/docs")


# Middleware: log requests and catch+log unhandled exceptions with full traceback
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = f"{request.method} {request.url.path}"
    log.debug(f"-> {request_id}")
    try:
        response = await call_next(request)
        log.debug(f"<- {request_id} {response.status_code}")
        return response
    except Exception as exc:
        tb = traceback.format_exc()
        # Log full traceback and request info
        log.error("Unhandled exception during request %s:\n%s", request_id, tb)
        # Ensure logs are flushed for Docker/Coolify
        for h in logging.root.handlers:
            try:
                h.flush()
            except Exception:
                pass
        # Return JSON 500 so clients receive a controlled response
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

# Mount all app routers under /api/v2 so UI can reach them at /api/v2/...
API_PREFIX = "/api/v2"

app.include_router(market_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(credentials_router, prefix=API_PREFIX)
app.include_router(settings_router, prefix=API_PREFIX)
app.include_router(ws_router, prefix=API_PREFIX)
app.include_router(commodity_router, prefix=API_PREFIX)
app.include_router(positions_router, prefix=API_PREFIX)
app.include_router(orders_router, prefix=API_PREFIX)
app.include_router(mock_exchange_router, prefix=API_PREFIX)
app.include_router(option_chain_router, prefix=API_PREFIX + "/options")
app.include_router(admin_router, prefix=API_PREFIX)
from app.rest.option_chain_compat import router as option_chain_compat_router
app.include_router(option_chain_compat_router, prefix=API_PREFIX)
# Backward compatibility for older frontend calls (v1)
import os as _os
_disable_v1 = (_os.getenv("DISABLE_V1_COMPAT") or "").strip().lower() in ("1","true","yes","on")
if not _disable_v1:
    app.include_router(credentials_router, prefix="/api/v1")
    app.include_router(settings_router, prefix="/api/v1")

# Backstop admin route for tests: set market depth
from app.market.market_state import state as market_state


@app.post(API_PREFIX + "/admin/market/depth")
async def set_market_depth(req: Request):
    payload = await req.json()
    sym = payload.get("symbol")
    depth = payload.get("depth")
    if not sym or not isinstance(depth, dict):
        return {"error": "symbol and depth required"}
    key = (sym or "").upper().strip()
    market_state.setdefault("depth", {})[key] = depth
    return {"status": "ok", "symbol": key, "depth": depth}

