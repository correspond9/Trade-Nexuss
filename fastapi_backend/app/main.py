from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(title="Trading Nexus API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

@app.get("/test")
def test():
    return {"message": "test route active"}

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

