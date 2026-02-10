from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ============================================================

# AUTO IMPORT ALL REST ROUTERS

# This loads every router inside app/rest automatically.

# You will never need to manually include routers again.

# ============================================================

import pkgutil
import importlib
from app import rest

app = FastAPI(title="Trading Nexus API")

# ---------------- CORS ----------------

app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)

# ---------------- Base routes ----------------

@app.get("/")
def root():
return {"message": "Trading Nexus API running"}

@app.get("/health")
def health():
return {"status": "ok"}

@app.get("/test")
def test():
return {"message": "test route active"}

# ============================================================

# AUTO ROUTER LOADER

# Scans app/rest folder and attaches every router automatically

# ============================================================

def load_all_routers():
for module_info in pkgutil.iter_modules(rest.**path**):
module_name = module_info.name
module = importlib.import_module(f"app.rest.{module_name}")

```
    if hasattr(module, "router"):
        app.include_router(module.router)
        print(f"[ROUTER LOADED] app.rest.{module_name}")
```

load_all_routers()
