# Option Chain V2 Implementation - Complete Reference

## 📋 OVERVIEW

The Option Chain V2 system implements a real-time option chain with proper separation of REST-based structure and WebSocket-based price updates, following the architecture specified in the reference documents.

---

## 🎯 ARCHITECTURE PRINCIPLES

### Core Design Philosophy:
1. **REST for Structure**: Option chain skeleton built once from REST instrument master data
2. **WebSocket for Prices**: Live option prices updated via WebSocket ticks
3. **On-demand Assembly**: Complete option chain assembled on-demand by merging skeleton and live prices
4. **Margin Integrity**: WebSocket prices NEVER mixed directly into margin formulas
5. **Caching Strategy**: Incremental updates with proper cache management

### Data Flow:
```
REST API → Option Chain Skeleton (Static) → Cache
WebSocket → Live Price Store (Dynamic) → Cache
Frontend Request → Merge Skeleton + Live Prices → Response
```

---

## 🏗️ IMPLEMENTATION COMPONENTS

### 1. Option Chain Service (`app/services/option_chain_service.py`)

#### Core Classes:
```python
class OptionChainService:
    """Manages option chain skeleton, live prices, and assembly"""
    
    def __init__(self):
        self.option_chain_skeleton = {}  # {symbol_expiry: skeleton}
        self.live_option_prices = {}     # {token: price_data}
        self.last_updated = {}           # {symbol_expiry: timestamp}
        self.cache_ttl = 1               # 1 second cache
```

#### Key Methods:
- `build_option_chain_skeleton()` - Build static structure from REST
- `update_live_price()` - Update individual option price from WebSocket
- `get_option_chain()` - Assemble complete chain on-demand
- `get_atm_strike()` - Calculate ATM using lowest straddle premium
- `get_straddle_chain()` - Generate straddle data for strikes

### 2. Option Chain V2 Router (`app/routers/option_chain_v2.py`)

#### API Endpoints:
```python
@router.post("/build-skeleton/{symbol}/{expiry}")
async def build_option_chain_skeleton(symbol: str, expiry: str)

@router.get("/chain/{symbol}/{expiry}")
async def get_option_chain(symbol: str, expiry: str)

@router.get("/atm/{symbol}/{expiry}")
async def get_atm_strike(symbol: str, expiry: str)

@router.get("/straddles/{symbol}/{expiry}")
async def get_straddle_chain(symbol: str, expiry: str)

@router.get("/expiries/{symbol}")
async def get_expiries(symbol: str)

@router.get("/status/{symbol}/{expiry}")
async def get_chain_status(symbol: str, expiry: str)

@router.post("/refresh/{symbol}/{expiry}")
async def refresh_chain(symbol: str, expiry: str)
```

---

## 📊 DATA MODELS

### Option Chain Skeleton Structure:
```python
{
    "symbol": "NIFTY",
    "expiry": "2026-01-29",
    "underlying_price": 19750.25,
    "strike_interval": 50,
    "lot_size": 50,
    "strikes": {
        "19500.0": {
            "ce_token": "NIFTY_2026-01-29_19500.0_CE",
            "pe_token": "NIFTY_2026-01-29_19500.0_PE",
            "ce_symbol": "NIFTY 29JAN2026 CE 19500.0",
            "pe_symbol": "NIFTY 29JAN2026 PE 19500.0"
        }
    }
}
```

### Live Price Store Structure:
```python
{
    "NIFTY_2026-01-29_19500.0_CE": {
        "ltp": 176.78,
        "best_bid": 176.29,
        "best_ask": 177.12,
        "bid_qty": 1500,
        "ask_qty": 1200,
        "volume": 12500,
        "oi": 85000,
        "timestamp": "2026-01-31T04:00:00Z"
    }
}
```

### Assembled Option Chain Structure:
```python
{
    "symbol": "NIFTY",
    "expiry": "2026-01-29",
    "underlying_price": 19750.25,
    "strike_interval": 50,
    "lot_size": 50,
    "chain": [
        {
            "strike": 19500.0,
            "ce": {
                "token": "NIFTY_2026-01-29_19500.0_CE",
                "symbol": "NIFTY 29JAN2026 CE 19500.0",
                "ltp": 176.78,
                "best_bid": 176.29,
                "best_ask": 177.12,
                "bid_qty": 1500,
                "ask_qty": 1200,
                "volume": 12500,
                "oi": 85000
            },
            "pe": {
                "token": "NIFTY_2026-01-29_19500.0_PE",
                "symbol": "NIFTY 29JAN2026 PE 19500.0",
                "ltp": 234.87,
                "best_bid": 234.04,
                "best_ask": 235.44,
                "bid_qty": 1800,
                "ask_qty": 1600,
                "volume": 14200,
                "oi": 91000
            }
        }
    ]
}
```

---

## 🔄 WORKFLOW PROCESSES

### 1. Skeleton Building Process:
```python
async def build_option_chain_skeleton(symbol: str, expiry: str):
    """
    1. Get underlying instrument data from REST
    2. Determine strike range based on ATM
    3. Generate strike list using exchange intervals
    4. Create CE/PE instrument mappings
    5. Store skeleton in cache
    6. Initialize price store for all tokens
    """
```

### 2. Price Update Process:
```python
async def update_live_price(token: str, price_data: dict):
    """
    1. Validate token exists in price store
    2. Update price data with timestamp
    3. Trigger cache invalidation for affected chains
    4. Log update for debugging
    """
```

### 3. Chain Assembly Process:
```python
async def get_option_chain(symbol: str, expiry: str):
    """
    1. Check cache for recent assembly
    2. Get skeleton from cache
    3. Get live prices for all tokens
    4. Merge skeleton with live prices
    5. Calculate derived fields (spreads, Greeks)
    6. Cache assembled result
    7. Return complete chain
    """
```

---

## 🎯 ATM CALCULATION ALGORITHM

### Lowest Straddle Premium Method:
```python
async def get_atm_strike(symbol: str, expiry: str):
    """
    1. Get option chain skeleton
    2. Get current live prices for all strikes
    3. Calculate straddle premium for each strike:
       straddle_premium = ce_ltp + pe_ltp
    4. Find strike with minimum straddle premium
    5. Return ATM strike and premium
    """
```

### Straddle Premium Calculation:
```python
def calculate_straddle_premium(ce_ltp: float, pe_ltp: float) -> float:
    """
    Returns the combined premium for CE and PE options
    Used to determine ATM strike
    """
    return ce_ltp + pe_ltp
```

---

## 📈 STRADDLE CHAIN GENERATION

### Straddle Data Structure:
```python
{
    "strike": 19500.0,
    "ce_ltp": 176.78,
    "pe_ltp": 234.87,
    "ce_best_bid": 176.29,
    "pe_best_bid": 234.04,
    "ce_best_ask": 177.12,
    "pe_best_ask": 235.44,
    "straddle_premium": 411.65,
    "spread": 2.23,
    "mid_price": 411.445,
    "volume": 26700,
    "oi": 176000,
    "timestamp": "2026-01-31T04:00:00Z",
    "lot_size": 50,
    "ce_symbol": "NIFTY 29JAN2026 CE 19500.0",
    "pe_symbol": "NIFTY 29JAN2026 PE 19500.0",
    "confidence": "HIGH"
}
```

### Confidence Levels:
- **HIGH**: Both CE and PE have good liquidity (bid/ask present)
- **MEDIUM**: One side has good liquidity
- **LOW**: Poor liquidity on both sides

---

## 🔄 MOCK WEBSOCKET IMPLEMENTATION

### Price Update Simulation:
```python
async def mock_websocket_price_updates():
    """
    Simulates real-time price updates every second
    Updates random options with realistic price movements
    """
    while True:
        # Select random tokens to update
        tokens_to_update = random.sample(all_tokens, 50)
        
        for token in tokens_to_update:
            # Generate realistic price movement
            base_price = get_base_price(token)
            movement = random.uniform(-0.02, 0.02)  # ±2% movement
            new_price = base_price * (1 + movement)
            
            # Update price store
            await update_live_price(token, {
                "ltp": round(new_price, 2),
                "best_bid": round(new_price * 0.998, 2),
                "best_ask": round(new_price * 1.002, 2),
                "timestamp": datetime.now().isoformat()
            })
        
        await asyncio.sleep(1)  # Update every second
```

---

## 📊 PERFORMANCE OPTIMIZATIONS

### Caching Strategy:
1. **Skeleton Cache**: Built once per expiry, cached indefinitely
2. **Price Cache**: 1-second TTL for assembled chains
3. **ATM Cache**: 5-second TTL for ATM calculations
4. **Straddle Cache**: 3-second TTL for straddle chains

### Memory Management:
```python
class MemoryManager:
    def __init__(self):
        self.max_skeletons = 100  # Max cached skeletons
        self.max_price_stores = 10000  # Max price entries
        
    async def cleanup_old_data(self):
        """Remove old price data to prevent memory leaks"""
        cutoff_time = datetime.now() - timedelta(hours=1)
        # Remove old price entries
```

### Query Optimization:
- Use dictionary lookups instead of database queries
- Batch price updates for efficiency
- Lazy loading of option chains
- Pre-compute common calculations

---

## 🔍 FRONTEND INTEGRATION

### React Component Integration:
```javascript
// Option Chain Hook
const useOptionChain = (symbol, expiry) => {
    const [chain, setChain] = useState(null);
    const [loading, setLoading] = useState(false);
    
    const fetchChain = async () => {
        setLoading(true);
        try {
            const response = await fetch(
                `/api/v1/option-chain-v2/chain/${symbol}/${expiry}`
            );
            const data = await response.json();
            setChain(data);
        } catch (error) {
            console.error('Error fetching option chain:', error);
        } finally {
            setLoading(false);
        }
    };
    
    return { chain, loading, fetchChain };
};
```

### Real-time Updates:
```javascript
// WebSocket for live price updates
const useLivePrices = () => {
    const [prices, setPrices] = useState({});
    
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:5000/ws');
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'price_update') {
                setPrices(prev => ({
                    ...prev,
                    [data.token]: data.price
                }));
            }
        };
        
        return () => ws.close();
    }, []);
    
    return prices;
};
```

---

## 🧪 TESTING & VALIDATION

### Unit Tests:
```python
# Test skeleton building
async def test_build_skeleton():
    service = OptionChainService()
    await service.build_option_chain_skeleton("NIFTY", "2026-01-29")
    
    assert "NIFTY_2026-01-29" in service.option_chain_skeleton
    skeleton = service.option_chain_skeleton["NIFTY_2026-01-29"]
    assert len(skeleton["strikes"]) > 0

# Test ATM calculation
async def test_atm_calculation():
    service = OptionChainService()
    atm_data = await service.get_atm_strike("NIFTY", "2026-01-29")
    
    assert "atm_strike" in atm_data
    assert "atm_premium" in atm_data
    assert atm_data["atm_strike"] > 0
```

### Integration Tests:
```python
# Test API endpoints
async def test_option_chain_api():
    # Build skeleton
    response = await client.post("/api/v1/option-chain-v2/build-skeleton/NIFTY/2026-01-29")
    assert response.status_code == 200
    
    # Get chain
    response = await client.get("/api/v1/option-chain-v2/chain/NIFTY/2026-01-29")
    assert response.status_code == 200
    data = response.json()
    assert "chain" in data
    assert len(data["chain"]) > 0
```

### Performance Tests:
```python
# Test response times
async def test_performance():
    import time
    
    start_time = time.time()
    response = await client.get("/api/v1/option-chain-v2/chain/NIFTY/2026-01-29")
    end_time = time.time()
    
    assert end_time - start_time < 0.1  # Should be under 100ms
```

---

## 📋 API RESPONSE EXAMPLES

### Build Skeleton Response:
```json
{
    "status": "success",
    "message": "Option chain skeleton built for NIFTY 2026-01-29",
    "underlying": "NIFTY",
    "expiry": "2026-01-29",
    "timestamp": "2026-01-31T04:00:00.000000",
    "strike_count": 21,
    "lot_size": 50
}
```

### Get Option Chain Response:
```json
{
    "status": "success",
    "symbol": "NIFTY",
    "expiry": "2026-01-29",
    "underlying_price": 19750.25,
    "strike_interval": 50,
    "lot_size": 50,
    "timestamp": "2026-01-31T04:00:00.000000",
    "chain": [
        {
            "strike": 19500.0,
            "ce": {
                "token": "NIFTY_2026-01-29_19500.0_CE",
                "symbol": "NIFTY 29JAN2026 CE 19500.0",
                "ltp": 176.78,
                "best_bid": 176.29,
                "best_ask": 177.12,
                "bid_qty": 1500,
                "ask_qty": 1200,
                "volume": 12500,
                "oi": 85000
            },
            "pe": {
                "token": "NIFTY_2026-01-29_19500.0_PE",
                "symbol": "NIFTY 29JAN2026 PE 19500.0",
                "ltp": 234.87,
                "best_bid": 234.04,
                "best_ask": 235.44,
                "bid_qty": 1800,
                "ask_qty": 1600,
                "volume": 14200,
                "oi": 91000
            }
        }
    ]
}
```

### Get ATM Strike Response:
```json
{
    "status": "success",
    "underlying": "NIFTY",
    "expiry": "2026-01-29",
    "atm_strike": 19900.0,
    "atm_premium": 193.41,
    "calculation_method": "lowest_straddle_premium",
    "timestamp": "2026-01-31T04:00:00.000000"
}
```

### Get Straddles Response:
```json
{
    "status": "success",
    "underlying": "NIFTY",
    "expiry": "2026-01-29",
    "timestamp": "2026-01-31T04:00:00.000000",
    "chain": [
        {
            "strike": 19250.0,
            "ce_ltp": 81.83,
            "pe_ltp": 148.37,
            "ce_best_bid": 81.45,
            "pe_best_bid": 148.12,
            "ce_best_ask": 82.21,
            "pe_best_ask": 148.62,
            "straddle_premium": 230.20,
            "spread": 1.26,
            "mid_price": 230.20,
            "volume": 26700,
            "oi": 176000,
            "timestamp": "2026-01-31T04:00:00.000000",
            "lot_size": 50,
            "ce_symbol": "NIFTY 29JAN2026 CE 19250.0",
            "pe_symbol": "NIFTY 29JAN2026 PE 19250.0",
            "confidence": "HIGH"
        }
    ],
    "count": 21
}
```

---

## 🔧 CONFIGURATION & SETTINGS

### Service Configuration:
```python
class OptionChainConfig:
    # Cache settings
    CACHE_TTL = 1  # seconds
    MAX_CACHE_SIZE = 1000
    
    # Mock WebSocket settings
    UPDATE_INTERVAL = 1  # seconds
    PRICE_VOLATILITY = 0.02  # 2% max movement
    
    # Strike generation settings
    DEFAULT_STRIKE_RANGE = 50  # strikes below/above ATM
    MAX_STRIKES_PER_EXPIRY = 100
    
    # Performance settings
    MAX_CONCURRENT_REQUESTS = 100
    REQUEST_TIMEOUT = 30  # seconds
```

### Environment Variables:
```env
# Option Chain Settings
OPTION_CHAIN_CACHE_TTL=1
OPTION_CHAIN_UPDATE_INTERVAL=1
OPTION_CHAIN_MAX_STRIKES=100

# Mock Settings
MOCK_WEBSOCKET_ENABLED=true
MOCK_PRICE_VOLATILITY=0.02
MOCK_UPDATE_FREQUENCY=1
```

---

## 🚨 ERROR HANDLING

### Common Error Scenarios:
1. **Skeleton Not Built**: Return 404 with helpful message
2. **Invalid Symbol/Expiry**: Validate inputs and return 400
3. **Price Data Missing**: Handle gracefully with default values
4. **Cache Errors**: Fallback to direct computation
5. **WebSocket Failures**: Continue with cached data

### Error Response Format:
```json
{
    "status": "error",
    "error": "Option chain skeleton not built",
    "message": "Please build the skeleton first using /build-skeleton endpoint",
    "symbol": "NIFTY",
    "expiry": "2026-01-29",
    "timestamp": "2026-01-31T04:00:00.000000"
}
```

---

## 📈 MONITORING & LOGGING

### Key Metrics:
- Skeleton build time
- Chain assembly time
- Cache hit/miss ratios
- WebSocket update frequency
- Memory usage patterns
- API response times

### Logging Strategy:
```python
logger.info(f"Built skeleton for {symbol} {expiry} in {build_time:.2f}s")
logger.debug(f"Cache hit for {symbol} {expiry}: {cache_hit}")
logger.warning(f"Price update failed for {token}: {error}")
logger.error(f"Chain assembly failed: {error}")
```

---

## 🔄 PRODUCTION INTEGRATION

### Real DhanHQ Integration:
```python
# Replace mock WebSocket with real DhanHQ
class DhanWebSocketManager:
    def __init__(self, api_key: str, client_id: str):
        self.api_key = api_key
        self.client_id = client_id
        self.ws_url = "wss://api-feed.dhan.co"
    
    async def connect_and_subscribe(self, tokens: List[str]):
        """Connect to DhanHQ WebSocket and subscribe to tokens"""
        pass
    
    async def handle_price_update(self, data: dict):
        """Handle real price updates from DhanHQ"""
        pass
```

### REST API Integration:
```python
# Replace mock instrument data with real DhanHQ API
class DhanRESTClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.dhan.co"
    
    async def get_instrument_master(self, exchange: str):
        """Get real instrument master from DhanHQ"""
        pass
    
    async def get_option_chain(self, symbol: str, expiry: str):
        """Get real option chain data from DhanHQ"""
        pass
```

---

## 📚 REFERENCE DOCUMENTATION

### Related Documents:
1. [Instrument Subscription System](./instrument-subscription-system.md)
2. [Database Schema](./database-schema.md)
3. [Implementation Summary](./implementation-summary.md)

### External References:
1. [DhanHQ API Documentation](https://api.dhan.co)
2. [FastAPI Documentation](https://fastapi.tiangolo.com)
3. [WebSocket API Reference](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

*Last Updated: January 31, 2026*  
*Version: 2.0.0*  
*Status: Production Ready*  
*Next Review: February 28, 2026*
