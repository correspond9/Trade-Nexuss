from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# import routers
from app.rest.market_api_v2 import router as market_router
from app.rest.credentials import router as credentials_router
from app.rest.auth import router as auth_router
from app.rest.settings import router as settings_router
from app.rest.ws import router as ws_router
from app.rest.commodity_rest import router as commodity_router


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

# Attach market router
app.include_router(market_router)
app.include_router(auth_router)
app.include_router(credentials_router)
app.include_router(settings_router)
app.include_router(ws_router)
app.include_router(commodity_router)
