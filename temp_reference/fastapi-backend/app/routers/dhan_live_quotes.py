"""
Dhan Live Quotes Router
Direct REST API integration with DhanHQ for NIFTY and SENSEX quotes
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import aiohttp
import asyncio
import json
import os
from datetime import datetime

router = APIRouter()

# Dhan API configuration
DHAN_BASE_URL = "https://api.dhan.co/v2"

# Index instrument tokens (based on Dhan documentation)
INDEX_TOKENS = {
    "NIFTY": {
        "security_id": "260105",
        "exchange_segment": "NSE_IDX"  # Try NSE_IDX first
    },
    "SENSEX": {
        "security_id": "260107", 
        "exchange_segment": "BSE_IDX"   # Try BSE_IDX first
    }
}

# Alternative segments to try if main ones fail
ALTERNATIVE_SEGMENTS = {
    "NIFTY": [
        {"exchange_segment": "NSE_IDX", "security_id": "260105"},
        {"exchange_segment": "NSE_FNO", "security_id": "260105"},
        {"exchange_segment": "NSE_INDEX", "security_id": "260105"}
    ],
    "SENSEX": [
        {"exchange_segment": "BSE_IDX", "security_id": "260107"},
        {"exchange_segment": "BSE_FNO", "security_id": "22"},
        {"exchange_segment": "BSE_INDEX", "security_id": "260107"}
    ]
}

async def get_dhan_credentials() -> Dict[str, str]:
    """Load Dhan credentials from file"""
    try:
        creds_file = os.path.join(os.path.dirname(__file__), '..', '..', 'dhan_credentials.json')
        
        if not os.path.exists(creds_file):
            raise HTTPException(status_code=500, detail="Credentials file not found")
            
        with open(creds_file, 'r') as f:
            creds_data = json.load(f)
        
        active_mode = creds_data.get('active_mode', 'DAILY_TOKEN')
        creds = creds_data.get(active_mode, {})
        
        if not creds.get('access_token'):
            raise HTTPException(status_code=500, detail="No access token found")
            
        return {
            "access_token": creds['access_token'],
            "client_id": creds['client_id']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load credentials: {e}")

@router.get("/live-quotes")
async def get_live_quotes():
    """Get live quotes for NIFTY and SENSEX using Dhan REST API"""
    try:
        # Get credentials
        creds = await get_dhan_credentials()
        
        # Prepare headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "access-token": creds["access_token"],
            "client-id": creds["client_id"]
        }
        
        # Prepare request body for LTP API
        request_body = {
            "NSE_IDX": [INDEX_TOKENS["NIFTY"]["security_id"]],
            "BSE_IDX": [INDEX_TOKENS["SENSEX"]["security_id"]]
        }
        
        async with aiohttp.ClientSession() as session:
            # Call Dhan LTP API
            async with session.post(
                f"{DHAN_BASE_URL}/marketfeed/ltp",
                headers=headers,
                json=request_body,
                timeout=10
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status") == "success":
                        # Extract quotes
                        quotes = {}
                        
                        # Extract NIFTY
                        nifty_data = data["data"].get("NSE_IDX", {}).get(INDEX_TOKENS["NIFTY"]["security_id"], {})
                        if nifty_data:
                            quotes["NIFTY"] = {
                                "price": nifty_data.get("last_price", 0),
                                "status": "success",
                                "timestamp": datetime.now().isoformat()
                            }
                        
                        # Extract SENSEX  
                        sensex_data = data["data"].get("BSE_IDX", {}).get(INDEX_TOKENS["SENSEX"]["security_id"], {})
                        if sensex_data:
                            quotes["SENSEX"] = {
                                "price": sensex_data.get("last_price", 0),
                                "status": "success", 
                                "timestamp": datetime.now().isoformat()
                            }
                        
                        return {
                            "status": "success",
                            "data": quotes,
                            "source": "Dhan REST API",
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        raise HTTPException(status_code=500, detail=f"Dhan API error: {data}")
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Dhan API returned {response.status}: {error_text}")
                    
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Network error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.get("/quote/{symbol}")
async def get_single_quote(symbol: str):
    """Get single quote for NIFTY or SENSEX - tries multiple segments"""
    symbol = symbol.upper()
    
    if symbol not in ALTERNATIVE_SEGMENTS:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not supported. Use NIFTY or SENSEX")
    
    # Check if market is open (9:15 AM to 3:30 PM IST)
    # Note: Sunday is usually closed but today is a special working day
    from datetime import datetime, timedelta
    # Convert UTC to IST (UTC + 5:30)
    ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
    current_time = ist_time.hour * 60 + ist_time.minute
    market_open = 9 * 60 + 15  # 9:15 AM = 555 minutes
    market_close = 15 * 60 + 30  # 3:30 PM = 930 minutes
    
    # Check if it's Sunday (weekday() == 6) and not a special working day
    # Note: Today is a special working Sunday, so allow Sunday trading
    is_sunday = ist_time.weekday() == 6
    is_special_working_sunday = True  # Override for today's special trading session
    
    if (is_sunday and not is_special_working_sunday) or not (market_open <= current_time <= market_close):
        return {
            "status": "error",
            "message": f"Market is closed. Current IST time: {ist_time.strftime('%H:%M')}",
            "symbol": symbol,
            "source": "market_closed",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        # Get credentials
        creds = await get_dhan_credentials()
        
        # Prepare headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json", 
            "access-token": creds["access_token"],
            "client-id": creds["client_id"]
        }
        
        async with aiohttp.ClientSession() as session:
            # Try each alternative segment for this symbol
            for segment_info in ALTERNATIVE_SEGMENTS[symbol]:
                try:
                    # Prepare request body
                    request_body = {
                        segment_info["exchange_segment"]: [segment_info["security_id"]]
                    }
                    
                    # Call Dhan LTP API
                    async with session.post(
                        f"{DHAN_BASE_URL}/marketfeed/ltp",
                        headers=headers,
                        json=request_body,
                        timeout=10
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            
                            if data.get("status") == "success":
                                # Extract quote
                                quote_data = data["data"].get(segment_info["exchange_segment"], {}).get(segment_info["security_id"], {})
                                
                                if quote_data and quote_data.get("last_price", 0) > 0:
                                    return {
                                        "status": "success",
                                        "data": {
                                            "symbol": symbol,
                                            "last_price": quote_data.get("last_price", 0),
                                            "exchange_segment": segment_info["exchange_segment"],
                                            "security_id": segment_info["security_id"]
                                        },
                                        "source": "Dhan REST API (Live)",
                                        "timestamp": datetime.now().isoformat()
                                    }
                        
                        # If this segment didn't work, try the next one
                        continue
                        
                except Exception as e:
                    # Try next segment
                    continue
            
            # If all segments failed
            return {
                "status": "error",
                "message": f"No data received for {symbol} - tried all segments",
                "symbol": symbol,
                "source": "api_error",
                "timestamp": datetime.now().isoformat()
            }
                    
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Network error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
