#!/usr/bin/env python3
"""
Test DhanHQ WebSocket connection with current credentials
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi_backend'))

from app.storage.db import SessionLocal
from app.storage.models import DhanCredential
from dhanhq import dhanhq as DhanHQClient
from dhanhq import MarketFeed

def test_websocket_connection():
    """Test WebSocket connection with current credentials"""
    print("🔍 Testing DhanHQ WebSocket connection...")
    
    # Load credentials
    db = SessionLocal()
    creds = db.query(DhanCredential).first()
    db.close()
    
    if not creds:
        print("❌ No credentials found in database")
        return False
    
    print(f"📋 Using credentials: Client ID {creds.client_id[:8]}...")
    
    try:
        # Create client
        client = DhanHQClient(
            client_id=creds.client_id,
            access_token=creds.auth_token
        )
        print("✅ DhanHQ client created successfully")
        
        # Test basic API call first
        print("🔍 Testing basic API access...")
        profile = client.get_profile()
        if profile:
            print("✅ Basic API access working")
        else:
            print("❌ Basic API access failed")
            return False
        
        # Test WebSocket connection
        print("🔍 Testing WebSocket connection...")
        instruments = [('NSE', 26000, 15)]  # NIFTY 50 index
        
        market_feed = MarketFeed(
            dhan_client=client,
            instruments=instruments,
            version="v2"
        )
        print("✅ MarketFeed object created")
        
        # Try to connect (this will hang if it works)
        print("🔍 Attempting WebSocket connection (10 second timeout)...")
        import threading
        import time
        
        def connect_test():
            try:
                market_feed.run_forever()
            except Exception as e:
                print(f"❌ WebSocket connection failed: {e}")
        
        thread = threading.Thread(target=connect_test, daemon=True)
        thread.start()
        
        # Wait 10 seconds for connection
        time.sleep(10)
        
        print("🔍 Connection test completed")
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    test_websocket_connection()
