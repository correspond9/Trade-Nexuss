#!/usr/bin/env python3
"""
WebSocket Connection Diagnostic Script
Tests DhanHQ WebSocket connection and reports exact issues
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi_backend'))

from app.storage.db import SessionLocal
from app.storage.models import DhanCredential
from dhanhq import DhanContext, MarketFeed

def test_dhan_connection():
    """Test DhanHQ WebSocket connection directly"""
    print("🔍 Testing DhanHQ WebSocket Connection...")
    print("=" * 60)
    
    # Load credentials
    db = SessionLocal()
    try:
        creds = db.query(DhanCredential).filter(DhanCredential.is_default == True).first()
        if not creds:
            creds = db.query(DhanCredential).first()
    finally:
        db.close()
    
    if not creds:
        print("❌ No credentials found in database")
        return False
    
    print(f"✅ Found credentials:")
    print(f"   Client ID: {creds.client_id}")
    token = getattr(creds, "auth_token", None) or getattr(creds, "daily_token", None)
    print(f"   Token: {token[:20]}..." if token else "   Token: None")
    
    if not creds.client_id or not token:
        print("❌ Incomplete credentials")
        return False
    
    # Test connection
    try:
        print("\n🔌 Attempting WebSocket connection...")
        dhan_context = DhanContext(client_id=creds.client_id, access_token=token)
        
        # Test with minimal instruments (NIFTY index)
        test_instruments = [(0, "13", 15)]  # NIFTY index, ticker mode
        
        market_feed = MarketFeed(
            dhan_context=dhan_context,
            instruments=test_instruments,
            version="v2"
        )
        
        print("✅ MarketFeed object created successfully")
        print("🔄 Attempting to connect...")
        
        # Try to connect for 10 seconds
        import time
        import threading
        
        def connect_test():
            try:
                market_feed.run_forever()
            except Exception as e:
                print(f"❌ Connection error: {e}")
        
        connect_thread = threading.Thread(target=connect_test, daemon=True)
        connect_thread.start()
        
        # Wait for connection or timeout
        for i in range(10):
            time.sleep(1)
            print(f"⏳ Waiting... {i+1}/10 seconds")
            
            # Try to get data
            try:
                data = market_feed.get_data()
                if data:
                    print(f"✅ SUCCESS: Received data: {data}")
                    return True
            except:
                pass
        
        print("❌ TIMEOUT: No data received in 10 seconds")
        return False
        
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_socket_permissions():
    """Check if WebSocket connections are allowed"""
    print("\n🔍 Checking Socket Permissions...")
    print("=" * 60)
    
    try:
        import socket
        # Test creating a socket
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(5)
        
        # Try to connect to a known server
        print("🔌 Testing basic socket connectivity...")
        result = test_socket.connect_ex(("google.com", 443))
        test_socket.close()
        
        if result == 0:
            print("✅ Basic socket connectivity: OK")
        else:
            print(f"❌ Basic socket connectivity failed: {result}")
            return False
            
        # Test WebSocket-specific connection
        print("🔌 Testing WebSocket connectivity...")
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(5)
        result = test_socket.connect_ex(("api-feed.dhan.co", 443))
        test_socket.close()
        
        if result == 0:
            print("✅ WebSocket connectivity: OK")
        else:
            print(f"❌ WebSocket connectivity failed: {result}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Socket permission check failed: {e}")
        return False

def main():
    print("🚀 Trade-Nexuss WebSocket Diagnostic Tool")
    print("=" * 60)
    
    # Check socket permissions first
    if not check_socket_permissions():
        print("\n❌ Socket permission issues detected!")
        print("🔧 Possible solutions:")
        print("   1. Run as Administrator")
        print("   2. Check firewall settings")
        print("   3. Check antivirus blocking")
        print("   4. Check network proxy settings")
        return
    
    # Test DhanHQ connection
    if test_dhan_connection():
        print("\n✅ WebSocket connection test PASSED")
        print("🔧 The issue might be in the subscription logic")
    else:
        print("\n❌ WebSocket connection test FAILED")
        print("🔧 The issue is with DhanHQ connectivity")

if __name__ == "__main__":
    main()
