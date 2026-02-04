# Trading Terminal Project Structure

## 📁 Project Overview
This is a comprehensive trading terminal application with FastAPI backend, React frontend, and real-time market data integration with DhanHQ.

---

## 🏗️ Core Architecture

### **fastapi-backend/** - Main Backend Application
**Role**: Production-ready FastAPI backend with 37+ API endpoints, async operations, and DhanHQ integration

```
fastapi-backend/
├── app/                          # Core application package
│   ├── models/                   # Pydantic data models
│   │   ├── auth.py             # User authentication models
│   │   ├── trading.py          # Order, trade, position models
│   │   ├── market.py           # Market data, instrument models
│   │   └── portfolio.py        # Portfolio, holdings models
│   │
│   ├── routers/                 # API endpoint routers (37+ endpoints)
│   │   ├── auth.py             # Authentication endpoints (7)
│   │   ├── trading.py          # Trading operations (8)
│   │   ├── market.py           # Market data APIs (8)
│   │   ├── portfolio.py        # Portfolio management (6)
│   │   ├── admin.py            # Admin operations (8)
│   │   ├── dhan_websocket.py   # Dhan WebSocket integration
│   │   └── websocket.py        # Internal WebSocket server
│   │
│   ├── services/                # Business logic layer
│   │   ├── auth_service.py     # Authentication logic
│   │   ├── trading_service.py  # Order management
│   │   ├── market_service.py   # Market data processing
│   │   ├── dhan_websocket.py   # DhanHQ WebSocket client
│   │   └── instrument_master_service.py # Instrument universe
│   │
│   ├── middleware/              # Custom middleware
│   │   ├── security.py         # Security headers, CORS
│   │   └── rate_limit.py       # API rate limiting
│   │
│   ├── utils/                   # Utility functions
│   │   └── security.py         # Password hashing, JWT
│   │
│   ├── config.py               # Application configuration
│   ├── database.py             # Async database connections
│   └── dependencies.py         # Dependency injection
│
├── tests/                       # Test suite
├── migrations/                  # Database migrations
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Multi-container setup
├── .env                        # Environment variables
└── main.py                     # FastAPI application entry point
```

---

### **frontend/** - React Frontend Application
**Role**: Modern React trading interface with real-time data, charts, and order management

```
frontend/
├── public/                     # Static assets
│   ├── index.html             # HTML template
│   └── favicon.ico            # Application icon
│
├── src/                       # React source code
│   ├── components/            # Reusable UI components
│   │   ├── common/           # Shared components (buttons, inputs)
│   │   ├── charts/           # Trading charts, technical indicators
│   │   ├── forms/            # Order forms, search forms
│   │   ├── layout/           # Header, sidebar, navigation
│   │   └── tables/           # Data tables, watchlists
│   │
│   ├── pages/                # Page-level components
│   │   ├── Dashboard/        # Main trading dashboard
│   │   ├── Orders/           # Order management interface
│   │   ├── Portfolio/        # Portfolio view
│   │   ├── Market/           # Market data, watchlists
│   │   └── Settings/         # User settings
│   │
│   ├── hooks/                # Custom React hooks
│   │   ├── useWebSocket.js   # WebSocket connection management
│   │   ├── useMarketData.js  # Real-time market data
│   │   └── useAuth.js        # Authentication state
│   │
│   ├── services/             # API communication layer
│   │   ├── api.js           # HTTP client configuration
│   │   ├── auth.js          # Authentication API calls
│   │   ├── trading.js       # Trading operations
│   │   └── market.js        # Market data APIs
│   │
│   ├── utils/               # Helper functions
│   ├── styles/              # CSS/styling files
│   ├── App.jsx             # Main React application
│   └── main.jsx            # React entry point
│
├── package.json            # Node.js dependencies
├── vite.config.js          # Vite build configuration
└── .env                    # Frontend environment variables
```

---

## 🔧 Legacy Backend Systems

### **backend/** - Original Flask Backend
**Role**: Legacy Flask application being migrated to FastAPI

```
backend/
├── app/                    # Flask application
│   ├── __init__.py       # Flask app factory
│   ├── models/           # SQLAlchemy database models
│   ├── routes/           # Flask blueprints (30+ endpoints)
│   └── utils/            # Utility functions
│
├── broker/               # Broker integrations
│   ├── dhan/            # DhanHQ broker integration
│   ├── alice/           # Alice Blue integration
│   └── mock/            # Mock broker for testing
│
├── db/                  # Database files
│   ├── trading_terminal.db  # Main trading database
│   ├── latency.db           # Performance metrics
│   └── logs.db              # Application logs
│
└── requirements.txt     # Python dependencies
```

### **node-api-gateway/** - Node.js API Gateway
**Role**: API gateway for market data and external integrations

```
node-api-gateway/
├── src/
│   ├── controllers/      # Request handlers
│   ├── middleware/       # Express middleware
│   ├── routes/          # API routes
│   └── services/        # Business logic
│
├── package.json         # Node.js dependencies
└── server.js           # Express server entry point
```

---

## 📊 Data & Configuration

### **Database Files**
- **trading_terminal.db** - Main trading database (users, orders, positions)
- **latency.db** - Performance and latency metrics
- **logs.db** - Application logs and audit trails
- **sandbox.db** - Development/testing database

### **Configuration Files**
- **.env** - Environment variables (API keys, database URLs)
- **config.json** - Application configuration
- **package.json** - Node.js dependencies and scripts
- **requirements.txt** - Python dependencies

---

## 🔌 External Integrations

### **DhanHQ Integration**
- **dhan-websocket-client.js** - Real-time market data streaming
- **app/services/dhan_websocket.py** - Dhan WebSocket client
- **DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN** - API credentials

### **WebSocket Servers**
- **websocket-server.js** - Real-time data streaming (port 5003)
- **FastAPI WebSocket** - Internal WebSocket server (port 8765)

---

## 🧪 Testing & Development

### **Test Suites**
- **tests/** - Frontend tests (Jest, React Testing Library)
- **fastapi-backend/tests/** - Backend tests (pytest)
- **api.test.js** - API integration tests

### **Development Tools**
- **scripts/** - Utility scripts for setup and maintenance
- **utils/** - Development utilities
- **.continue/** - AI agent configurations

---

## 📦 Deployment & Infrastructure

### **Containerization**
- **Dockerfile** - FastAPI application container
- **docker-compose.yml** - Multi-container development setup

### **Security**
- **trading-terminal-key.pem/ppk** - SSL certificates
- **security-config.js** - Security configurations
- **setup-security.sh** - Security setup script

---

## 📈 Key Features by Component

### **FastAPI Backend (Port 5000)**
- ✅ 37+ REST API endpoints
- ✅ Async database operations
- ✅ JWT authentication
- ✅ Rate limiting
- ✅ Auto-generated API docs (/docs)
- ✅ DhanHQ WebSocket integration
- ✅ Real-time market data streaming

### **React Frontend (Port 5173)**
- ✅ Modern React with hooks
- ✅ Real-time data updates
- ✅ Trading charts and visualizations
- ✅ Order management interface
- ✅ Portfolio tracking
- ✅ Responsive design

### **Legacy Systems (Migration in Progress)**
- 🔄 Flask backend (being replaced by FastAPI)
- 🔄 Node.js API gateway (market data integration)
- ✅ Database migration completed

---

## 🚀 Current Status

**Production Ready**: FastAPI backend  
**Development**: Frontend integration  
**Migration**: 25% complete (Phase 1 of 4)  
**Next Phase**: Frontend-backend integration testing

---

**Total Files**: 500+ (excluding cache folders)  
**Technologies**: FastAPI, React, Python, JavaScript, SQLite, WebSocket  
**Architecture**: Microservices with real-time data streaming
