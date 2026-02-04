┌─────────────────────────────────────────────────────────────────────────┐

│                  BROKING TERMINAL V2 - CURRENT ARCHITECTURE             │

│                         (FastAPI + DhanHQ-py)                           │

└─────────────────────────────────────────────────────────────────────────┘





&nbsp;                       ╔═══════════════════════════╗

&nbsp;                       ║   DHAN HQ WEBSOCKET       ║

&nbsp;                       ║  wss://api-feed.dhan.co   ║

&nbsp;                       ║  (Live tick updates)      ║

&nbsp;                       ╚═════════════╤═════════════╝

&nbsp;                                     │

&nbsp;                                     │ Binary data stream

&nbsp;                                     │ (SecurityId + LTP)

&nbsp;                                     │

&nbsp;                   ┌─────────────────v─────────────────┐

&nbsp;                   │  app/dhan/live\_feed.py            │

&nbsp;                   │  ├─ DhanContext (JWT auth)        │

&nbsp;                   │  ├─ MarketFeed (WebSocket handler)│

&nbsp;                   │  └─ Binary decoder (bytes\[4:8], 

&nbsp;                   │                   bytes\[8:12])    │

&nbsp;                   └──────────────┬────────────────────┘

&nbsp;                                  │

&nbsp;                                  │ Decoded prices

&nbsp;                                  │

&nbsp;                   ┌──────────────v──────────────┐

&nbsp;                   │  app/market/live\_prices.py  │

&nbsp;                   │  (Thread-safe cache)        │

&nbsp;                   │                             │

&nbsp;                   │  {NIFTY: 24825.45}         │

&nbsp;                   │  {SENSEX: 80722.94}        │

&nbsp;                   │  {CRUDEOIL: 5673.00}       │

&nbsp;                   └──────┬──────────┬───────────┘

&nbsp;                          │          │

&nbsp;        ┌─────────────────┘          └──────────────────┐

&nbsp;        │                                               │

&nbsp;        ↓                                               ↓



&nbsp;   ┌────────────────────┐                   ┌─────────────────────────┐

&nbsp;   │  FRONTEND (React)  │                   │  FASTAPI Backend        │

&nbsp;   │                    │                   │  (app/main.py)          │

&nbsp;   │ ┌────────────────┐ │                   │                         │

&nbsp;   │ │ Place Order    │ │                   │  REST Endpoints:        │

&nbsp;   │ │  Form          │ │                   │  ├─ POST /orders        │

&nbsp;   │ │                │ │──────────────────▶│  ├─ GET /orders         │

&nbsp;   │ │ \[Symbol]       │ │    Submit Order   │  ├─ GET /positions      │

&nbsp;   │ │ \[Qty]          │ │                   │  ├─ GET /wallets        │

&nbsp;   │ │ \[Price]        │ │                   │  ├─ POST /users (admin) │

&nbsp;   │ └────────────────┘ │                   │  └─ GET /prices         │

&nbsp;   │                    │                   │                         │

&nbsp;   │ ┌────────────────┐ │                   │  WebSocket Endpoints:   │

&nbsp;   │ │ Orderbook      │ │◀──────────────────│  ├─ /ws/prices (ticks)  │

&nbsp;   │ │ (live updates) │ │    Order Status   │  └─ /ws/orders (fills)  │

&nbsp;   │ │                │ │                   │                         │

&nbsp;   │ │ Ord | Qty | Px │ │                   │  Internal Modules:      │

&nbsp;   │ └────────────────┘ │                   │  ├─ oms/order\_router    │

&nbsp;   │                    │                   │  ├─ ems/matching\_engine │

&nbsp;   │ ┌────────────────┐ │                   │  ├─ ems/execution\_engine│

&nbsp;   │ │ Trade Feed     │ │                   │  ├─ trading/position    │

&nbsp;   │ │ (filled list)  │ │                   │  ├─ rms/margin\_calc     │

&nbsp;   │ │                │ │                   │  ├─ ledger/audit        │

&nbsp;   │ │ Trade | Px | PL │ │                   │  └─ users/auth + rbac   │

&nbsp;   │ └────────────────┘ │                   │                         │

&nbsp;   │                    │                   └──────────┬──────────────┘

&nbsp;   └────────────────────┘                             │

&nbsp;                                                      │

&nbsp;                                   ┌──────────────────┴──────────────────┐

&nbsp;                                   │                                     │

&nbsp;                                   ↓                                     ↓

&nbsp;                       ┌──────────────────────┐         ┌──────────────────────┐

&nbsp;                       │   SQLITE DATABASE    │         │  Instrument Master   │

&nbsp;                       │   (VPS-ready)        │         │  (CSV loader)        │

&nbsp;                       │                      │         │                      │

&nbsp;                       │ Tables:              │         │  api-scrip-master    │

&nbsp;                       │ ├─ orders            │         │  -detailed.csv       │

&nbsp;                       │ ├─ order\_legs        │         │ (289,298 instruments)│

&nbsp;                       │ ├─ trades            │         │                      │

&nbsp;                       │ ├─ positions         │         │ ├─ NIFTY (13)        │

&nbsp;                       │ ├─ wallets           │         │ ├─ SENSEX (51)       │

&nbsp;                       │ ├─ ledger\_entries    │         │ ├─ CRUDEOIL (467013) │

&nbsp;                       │ ├─ dhan\_credentials  │         │ └─ ... 289k more     │

&nbsp;                       │ └─ users             │         └──────────────────────┘

&nbsp;                       └──────────────────────┘





&nbsp;                       ╔════════════════════════════╗

&nbsp;                       ║  DATA FLOW SEQUENCE        ║

&nbsp;                       ╠════════════════════════════╣

&nbsp;                       ║                            ║

&nbsp;                       ║ 1. Dhan WebSocket streams  ║

&nbsp;                       ║    binary tick data        ║

&nbsp;                       ║          ↓                 ║

&nbsp;                       ║ 2. DhanHQ-py decodes it   ║

&nbsp;                       ║          ↓                 ║

&nbsp;                       ║ 3. Cached in live\_prices  ║

&nbsp;                       ║          ↓                 ║

&nbsp;                       ║ 4. Frontend polls /prices  ║

&nbsp;                       ║    or subscribes /ws       ║

&nbsp;                       ║          ↓                 ║

&nbsp;                       ║ 5. User places order       ║

&nbsp;                       ║          ↓                 ║

&nbsp;                       ║ 6. FastAPI validates       ║

&nbsp;                       ║    (margin check vs REST)  ║

&nbsp;                       ║          ↓                 ║

&nbsp;                       ║ 7. Execution engine fills  ║

&nbsp;                       ║    order with bid/ask      ║

&nbsp;                       ║          ↓                 ║

&nbsp;                       ║ 8. Trade saved to DB       ║

&nbsp;                       ║          ↓                 ║

&nbsp;                       ║ 9. Position updated        ║

&nbsp;                       ║          ↓                 ║

&nbsp;                       ║ 10. Frontend refreshes UI  ║

&nbsp;                       ║    via WebSocket /orders   ║

&nbsp;                       ║                            ║

&nbsp;                       ╚════════════════════════════╝

