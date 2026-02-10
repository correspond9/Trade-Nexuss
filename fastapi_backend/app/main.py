from fastapi import FastAPI
import sys

app = FastAPI(title="Trading Nexus API")


# -----------------------------------------------------
# BASIC HEALTH ROUTES (always load)
# -----------------------------------------------------

@app.get("/")
def root():
    return {"message": "Trading Nexus API running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/test")
def test():
    return {"test": "working"}


# -----------------------------------------------------
# ROUTER LOADING (SAFE MODE)
# -----------------------------------------------------

def load_router(import_path, router_name="router", prefix=""):
    try:
        module = __import__(import_path, fromlist=[router_name])
        router = getattr(module, router_name)
        app.include_router(router, prefix=prefix)
        print(f"[ROUTER] Loaded: {import_path}", file=sys.stdout)
    except Exception as e:
        print(f"[ROUTER] FAILED: {import_path}", file=sys.stdout)
        print(e, file=sys.stdout)


# -----------------------------------------------------
# API ROUTERS
# -----------------------------------------------------

# MARKET API
load_router("app.rest.market_api_v2")

# FUTURE ROUTERS — add as project grows
# load_router("app.rest.broker")
# load_router("app.rest.orders")
# load_router("app.rest.auth")
# load_router("app.rest.websocket")


# -----------------------------------------------------
# STARTUP CONFIRMATION
# -----------------------------------------------------

@app.on_event("startup")
async def startup_event():
    print("[STARTUP] Trading Nexus API boot complete", file=sys.stdout)
