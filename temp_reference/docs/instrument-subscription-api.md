# Instrument Subscription API - Complete Reference

## 📡 API ENDPOINTS

### Base URL
```
http://127.0.0.1:5000/api/v1/instrument-subscription/
```

---

## 🔧 CORE ENDPOINTS

### 1. Generate Instrument Universe

**Endpoint**: `POST /generate-universe`

**Description**: Generate the complete instrument universe as per DhanHQ compliance

**Request**:
```bash
curl -X POST "http://127.0.0.1:5000/api/v1/instrument-subscription/generate-universe"
```

**Response**:
```json
{
  "status": "success",
  "message": "Instrument universe generated successfully",
  "timestamp": "2026-01-31T04:01:30.896288",
  "stats": {
    "total_instruments": 6400,
    "total_symbols": 25,
    "subscription_plans": 2,
    "search_index_size": 1881,
    "instruments_per_websocket": [5000, 1400],
    "instrument_types": {
      "OPTIDX": 5264,
      "OPTSTK": 1000,
      "FUTSTK": 20,
      "EQ": 10,
      "FUTCOM": 18,
      "OPTCOM": 88
    }
  }
}
```

**Use Cases**:
- System startup initialization
- Universe refresh after expiry rollover
- Admin-triggered universe regeneration

---

### 2. Search Instruments

**Endpoint**: `GET /search`

**Description**: Search instruments with relevance ranking

**Parameters**:
- `q` (required, min_length=2): Search query
- `limit` (optional, default=50, max=100): Maximum results

**Request**:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/search?q=NIFTY&limit=10"
```

**Response**:
```json
{
  "status": "success",
  "query": "NIFTY",
  "timestamp": "2026-01-31T04:01:34.010746",
  "count": 10,
  "results": [
    {
      "instrument": {
        "symbol": "NIFTY 50_21150.0_CE",
        "name": "NIFTY 50 21150.0 CE",
        "exchange": "NSE",
        "instrument_type": "OPTIDX",
        "token": "NIFTY 50_2026-03-12_21150.0_CE",
        "expiry": "2026-03-12",
        "strike": 21150.0,
        "option_type": "CE",
        "lot_size": 50,
        "tick_size": 0.05,
        "isin": null,
        "trading_session": "NORMAL"
      },
      "relevance_score": 80.0
    }
  ]
}
```

**Relevance Scoring**:
- Exact symbol match: 100 points
- Symbol starts with query: 80 points
- Query contained in symbol: 60 points
- Name starts with query: 70 points
- Query contained in name: 50 points
- Exchange match: 30 points
- Instrument type match: 25 points
- Option type match: 20 points

---

### 3. Search Suggestions (Autocomplete)

**Endpoint**: `GET /search-suggestions`

**Description**: Get search suggestions for autocomplete functionality

**Parameters**:
- `q` (required, min_length=1): Partial search query
- `limit` (optional, default=10, max=20): Maximum suggestions

**Request**:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/search-suggestions?q=NIF&limit=5"
```

**Response**:
```json
{
  "status": "success",
  "query": "NIF",
  "timestamp": "2026-01-31T04:01:45.123456",
  "suggestions": [
    {
      "symbol": "NIFTY 50_21150.0_CE",
      "name": "NIFTY 50 21150.0 CE",
      "token": "NIFTY 50_2026-03-12_21150.0_CE",
      "exchange": "NSE",
      "instrument_type": "OPTIDX",
      "relevance_score": 80.0
    }
  ]
}
```

---

### 4. Get Instrument by Token

**Endpoint**: `GET /instrument/{token}`

**Description**: Get detailed instrument information by token

**Parameters**:
- `token` (required): Instrument token

**Request**:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/instrument/NIFTY%2050_2026-03-12_21150.0_CE"
```

**Response**:
```json
{
  "status": "success",
  "timestamp": "2026-01-31T04:01:50.123456",
  "instrument": {
    "symbol": "NIFTY 50_21150.0_CE",
    "name": "NIFTY 50 21150.0 CE",
    "exchange": "NSE",
    "instrument_type": "OPTIDX",
    "token": "NIFTY 50_2026-03-12_21150.0_CE",
    "expiry": "2026-03-12",
    "strike": 21150.0,
    "option_type": "CE",
    "lot_size": 50,
    "tick_size": 0.05,
    "isin": null,
    "trading_session": "NORMAL"
  }
}
```

---

### 5. Get Instruments by Symbol

**Endpoint**: `GET /symbol/{symbol}`

**Description**: Get all instruments for a specific symbol

**Parameters**:
- `symbol` (required): Symbol name

**Request**:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/symbol/NIFTY%2050"
```

**Response**:
```json
{
  "status": "success",
  "symbol": "NIFTY 50",
  "timestamp": "2026-01-31T04:01:55.123456",
  "count": 5264,
  "instruments": [
    {
      "symbol": "NIFTY 50_21150.0_CE",
      "name": "NIFTY 50 21150.0 CE",
      "exchange": "NSE",
      "instrument_type": "OPTIDX",
      "token": "NIFTY 50_2026-03-12_21150.0_CE",
      "expiry": "2026-03-12",
      "strike": 21150.0,
      "option_type": "CE",
      "lot_size": 50,
      "tick_size": 0.05
    }
  ]
}
```

---

## 📊 SUBSCRIPTION MANAGEMENT ENDPOINTS

### 6. Get Subscription Plans

**Endpoint**: `GET /subscription-plans`

**Description**: Get WebSocket subscription distribution plans

**Request**:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/subscription-plans"
```

**Response**:
```json
{
  "status": "success",
  "timestamp": "2026-01-31T04:02:00.123456",
  "total_plans": 2,
  "max_instruments_per_websocket": 5000,
  "max_websocket_connections": 5,
  "plans": [
    {
      "websocket_id": 0,
      "instrument_count": 5000,
      "sample_tokens": [
        "NIFTY 50_2026-03-12_21150.0_CE",
        "BANKNIFTY_2026-03-12_44500.0_CE",
        "SENSEX_2026-03-12_66500.0_CE"
      ]
    },
    {
      "websocket_id": 1,
      "instrument_count": 1400,
      "sample_tokens": [
        "RELIANCE_EQ",
        "TCS_EQ",
        "HDFCBANK_EQ"
      ]
    }
  ]
}
```

---

### 7. Get Specific Subscription Plan

**Endpoint**: `GET /subscription-plan/{websocket_id}`

**Description**: Get detailed WebSocket subscription plan

**Parameters**:
- `websocket_id` (required): WebSocket connection ID

**Request**:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/subscription-plan/0"
```

**Response**:
```json
{
  "status": "success",
  "websocket_id": 0,
  "timestamp": "2026-01-31T04:02:05.123456",
  "instrument_count": 5000,
  "instruments": [
    "NIFTY 50_2026-03-12_21150.0_CE",
    "NIFTY 50_2026-03-12_21150.0_PE",
    "BANKNIFTY_2026-03-12_44500.0_CE",
    "BANKNIFTY_2026-03-12_44500.0_PE",
    "SENSEX_2026-03-12_66500.0_CE"
  ]
}
```

---

### 8. Get WebSocket for Token

**Endpoint**: `GET /websocket/{token}`

**Description**: Find which WebSocket connection handles a specific token

**Parameters**:
- `token` (required): Instrument token

**Request**:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/websocket/NIFTY%2050_2026-03-12_21150.0_CE"
```

**Response**:
```json
{
  "status": "success",
  "token": "NIFTY 50_2026-03-12_21150.0_CE",
  "websocket_id": 0,
  "timestamp": "2026-01-31T04:02:10.123456"
}
```

---

## 📈 STATISTICS ENDPOINTS

### 9. Get Subscription Statistics

**Endpoint**: `GET /stats`

**Description**: Get comprehensive subscription statistics

**Request**:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/stats"
```

**Response**:
```json
{
  "status": "success",
  "timestamp": "2026-01-31T04:02:15.123456",
  "stats": {
    "total_instruments": 6400,
    "total_symbols": 25,
    "subscription_plans": 2,
    "search_index_size": 1881,
    "instruments_per_websocket": [5000, 1400],
    "instrument_types": {
      "OPTIDX": 5264,
      "OPTSTK": 1000,
      "FUTSTK": 20,
      "EQ": 10,
      "FUTCOM": 18,
      "OPTCOM": 88
    }
  }
}
```

---

### 10. Get Universe Summary

**Endpoint**: `GET /universe-summary`

**Description**: Get summary of approved instrument universe

**Request**:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/universe-summary"
```

**Response**:
```json
{
  "status": "success",
  "timestamp": "2026-01-31T04:02:20.123456",
  "approved_universe": {
    "index_options": {
      "description": "NSE & BSE Index Options (CE & PE mandatory)",
      "instruments": ["NIFTY 50", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY", "BANKEX"],
      "details": {
        "NIFTY 50": {
          "exchange": "NSE",
          "expiries": 12,
          "strikes_per_expiry": 100,
          "strike_range": 50
        }
      }
    },
    "stock_options": {
      "description": "Top 100 NSE F&O Stock Options",
      "count": 100,
      "expiries": 2,
      "strikes_per_expiry": 25,
      "strike_range": 12
    },
    "stock_futures": {
      "description": "Top 100 NSE F&O Stock Futures",
      "count": 100,
      "expiries": 2
    },
    "equity": {
      "description": "Top 1000 NSE Equity Stocks",
      "count": 1000
    },
    "mcx_futures": {
      "description": "MCX Commodity Futures",
      "commodities": ["GOLD", "GOLDM", "GOLDMINI", "SILVER", "SILVERM", "SILVERMINI", "CRUDEOIL", "NATURALGAS", "COPPER"],
      "expiries": 2
    },
    "mcx_options": {
      "description": "MCX Commodity Options",
      "commodities": ["CRUDEOIL", "NATURALGAS"],
      "expiries": 2,
      "strikes_per_expiry": 10,
      "strike_range": 5
    }
  },
  "compliance_limits": {
    "max_websocket_connections": 5,
    "max_instruments_per_websocket": 5000,
    "rest_quote_apis_per_second": 1,
    "rest_data_apis_per_second": 5
  },
  "expected_counts": {
    "index_options": "~5,600",
    "stock_options": "~10,000",
    "stock_futures": "~200",
    "nse_equities": "~1,000",
    "mcx_futures": "~18",
    "mcx_options": "~80",
    "total": "~16,900"
  }
}
```

---

## 🔍 SEARCH EXAMPLES

### Example 1: Search for NIFTY Options
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/search?q=NIFTY%2050&limit=5"
```

### Example 2: Search for Stock Options
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/search?q=RELIANCE&limit=10"
```

### Example 3: Search for MCX Commodities
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/search?q=GOLD&limit=5"
```

### Example 4: Autocomplete Suggestions
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/search-suggestions?q=BANK&limit=10"
```

---

## 🚨 ERROR RESPONSES

### 400 Bad Request
```json
{
  "detail": "Search query cannot be empty"
}
```

### 404 Not Found
```json
{
  "detail": "Instrument not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error generating universe: Failed to generate instrument universe"
}
```

---

## 📊 PERFORMANCE METRICS

### Response Times:
- **Universe Generation**: ~2-3 seconds
- **Search Queries**: <100ms
- **Autocomplete**: <50ms
- **Statistics**: <10ms

### Rate Limits:
- **No explicit rate limiting** (subject to DhanHQ limits)
- **Recommended**: 100 requests/minute for search endpoints

---

## 🔧 INTEGRATION GUIDELINES

### 1. Frontend Integration
```javascript
// Search implementation
const searchInstruments = async (query, limit = 10) => {
  const response = await fetch(`/api/v1/instrument-subscription/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  return response.json();
};

// Autocomplete implementation
const getSearchSuggestions = async (query) => {
  const response = await fetch(`/api/v1/instrument-subscription/search-suggestions?q=${encodeURIComponent(query)}`);
  return response.json();
};
```

### 2. WebSocket Integration
```javascript
// Find WebSocket for instrument
const getWebSocketForToken = async (token) => {
  const response = await fetch(`/api/v1/instrument-subscription/websocket/${encodeURIComponent(token)}`);
  const data = await response.json();
  return data.websocket_id;
};
```

### 3. Error Handling
```javascript
try {
  const results = await searchInstruments(query);
  // Handle results
} catch (error) {
  if (error.status === 400) {
    // Handle bad request
  } else if (error.status === 404) {
    // Handle not found
  } else {
    // Handle server error
  }
}
```

---

## 📋 TESTING COMMANDS

### Generate Universe:
```bash
curl -X POST "http://127.0.0.1:5000/api/v1/instrument-subscription/generate-universe"
```

### Test Search:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/search?q=NIFTY&limit=5"
```

### Test Autocomplete:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/search-suggestions?q=NIF&limit=5"
```

### Get Stats:
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/instrument-subscription/stats"
```

---

*Last Updated: January 31, 2026*
*Version: 1.0.0*
*API Version: v1*
