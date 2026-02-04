# Baseline Snapshot - Working Setup
**Created:** 2026-02-01  
**Purpose:** Document current working configuration to lock as default

## Active Components

### Database Configuration
- **Primary Database:** `./databases/trading_terminal.db` (SQLite)
- **Config Location:** `fastapi-backend/app/config.py`
- **Database URL:** `sqlite+aiosqlite:///./databases/trading_terminal.db`

### WebSocket Integration
- **Service:** `app/services/dhan_websocket.py`
- **Price Store:** `app/services/websocket_price_store.py`
- **Underlying Store:** `app/services/underlying_price_store.py`
- **WebSocket URL:** `wss://api-feed.dhan.co`

### Active Routers (Main.py imports)
```
- simple_auth
- trading
- market
- portfolio
- admin
- dhan_websocket
- instrument_subscription
- option_chain_v2
- websocket
- instruments
- system
- simple_credentials
- dhan_auth
- last_close_bootstrap
- authoritative_option_chain
- option_chain
- option_chain_v2
- positions
- orders
- baskets
- expiry
- margin
```

### Active Services
```
- app/services/authoritative_option_chain_service.py
- app/services/auth_service.py
- app/services/credentials_service.py
- app/services/dhan_websocket.py
- app/services/instrument_subscription_service.py
- app/services/last_close_bootstrap.py
- app/services/ltp_storage_service.py
- app/services/market_service.py
- app/services/option_chain_service.py
- app/services/portfolio_service.py
- app/services/trading_service.py
- app/services/underlying_price_store.py
- app/services/websocket_price_store.py
```

## Key Features Status
- ✅ Dhan WebSocket connection active
- ✅ Real-time price caching functional
- ✅ Option chain v2 implemented
- ✅ Instrument subscription service working
- ✅ Underlying price store operational

## Configuration Files
- `fastapi-backend/app/config.py` - Main settings
- `fastapi-backend/app/database.py` - Database configuration
- `fastapi-backend/main.py` - Application entry point

## Database Schema
- Tables managed by SQLAlchemy models
- Location: `fastapi-backend/app/models/`

## Security
- JWT authentication implemented
- CORS configured for localhost ports
- Trusted hosts configured

## Notes
- This represents the WORKING configuration
- Any deviations from this baseline should be investigated
- WebSocket successfully connects and caches live data
- No mock data in production - uses real Dhan API
