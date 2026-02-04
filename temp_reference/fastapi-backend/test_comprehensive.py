#!/usr/bin/env python3
"""
Comprehensive DhanHQ API Test - Try All Approaches
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_all_approaches():
    """Test all possible approaches to find working one"""
    
    print("🧪 Comprehensive DhanHQ API Test")
    print("=" * 50)
    
    client_id = "1100353799"
    access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY5ODQzNjA5LCJpYXQiOjE3Njk3NTcyMDksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMzUzNzk5In0.bKl_DpJ8ePk5EqUTD4tWcSLvwBTgCzz2bZYwYqMcKkk5T___OJxXSIHfPTEKwz-7hkduQGCMebVDyjWPAuopLg"
    
    try:
        from dhanhq import dhanhq
        dhan = dhanhq(client_id, access_token.strip())
        
        print("📊 Testing different API methods...")
        
        # Test 1: ticker_data with different formats
        methods_to_test = [
            ("ticker_data (string)", lambda: dhan.ticker_data("13626")),
            ("ticker_data (list)", lambda: dhan.ticker_data(["13626"])),
            ("ticker_data (tuple)", lambda: dhan.ticker_data(("13626",))),
            ("get_order_book", lambda: dhan.get_order_book("13626")),
            ("quote_data", lambda: dhan.quote_data("13626")),
            ("fund_limits", lambda: dhan.get_fund_limits()),
            ("holdings", lambda: dhan.get_holdings()),
        ]
        
        for method_name, method_func in methods_to_test:
            try:
                print(f"\n🔍 Testing {method_name}...")
                result = method_func()
                print(f"📨 Result: {result}")
                
                if result and result.get('status') == 'success':
                    print(f"✅ {method_name} WORKS!")
                    return True
                else:
                    print(f"❌ {method_name} failed")
                    
            except Exception as e:
                print(f"❌ {method_name} error: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ dhanhq class error: {e}")
        return False

async def test_websocket_variations():
    """Test WebSocket with different instrument formats"""
    
    print("\n🔌 Testing WebSocket Variations")
    print("=" * 40)
    
    try:
        from dhanhq import DhanFeed
        
        client_id = "1100353799"
        access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY5ODQzNjA5LCJpYXQiOjE3Njk3NTcyMDksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMzUzNzk5In0.bKl_DpJ8ePk5EqUTD4tWcSLvwBTgCzz2bZYwYqMcKkk5T___OJxXSIHfPTEKwz-7hkduQGCMebVDyjWPAuopLg"
        
        # Different instrument formats to test
        test_cases = [
            ("V2 Ticker", "v2", [("NSE", "13626", "Ticker")]),
            ("V2 Quote", "v2", [("NSE", "13626", "Quote")]),
            ("V2 Full", "v2", [("NSE", "13626", "Full")]),
            ("V1 Ticker", "v1", [("NSE", "13626", "Ticker")]),
            ("V1 Quote", "v1", [("NSE", "13626", "Quote")]),
            ("V1 Full", "v1", [("NSE", "13626", "Full")]),
        ]
        
        for test_name, version, instruments in test_cases:
            try:
                print(f"\n🔍 Testing {test_name}...")
                data = DhanFeed(client_id, access_token.strip(), instruments, version)
                
                await data.connect()
                print(f"✅ {test_name} connected!")
                
                await data.subscribe_symbols(instruments)
                print(f"✅ {test_name} subscribed!")
                
                await data.disconnect()
                print(f"✅ {test_name} WORKS!")
                return True
                
            except Exception as e:
                print(f"❌ {test_name} failed: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        return False

async def test_direct_websocket():
    """Test direct WebSocket connection without library"""
    
    print("\n🌐 Testing Direct WebSocket")
    print("=" * 30)
    
    try:
        import websockets
        
        # Try different URL formats
        urls_to_test = [
            f"wss://api-feed.dhan.co?version=2&token={access_token}&clientId={client_id}&authType=2",
            f"wss://api-feed.dhan.co?version=1&token={access_token}&clientId={client_id}&authType=2",
            f"wss://api-feed.dhan.co?version=2&token={access_token}",
        ]
        
        for i, url in enumerate(urls_to_test, 1):
            try:
                print(f"\n🔍 Testing Direct WebSocket {i}...")
                print(f"📡 URL: {url[:80]}...")
                
                websocket = await websockets.connect(url, ping_interval=20, ping_timeout=10)
                print(f"✅ Direct WebSocket {i} connected!")
                
                # Try to keep connection alive
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    print(f"📨 Direct WebSocket {i}: Received data!")
                except asyncio.TimeoutError:
                    print(f"⏰ Direct WebSocket {i}: No data (but connected)")
                
                await websocket.close()
                return True
                
            except Exception as e:
                print(f"❌ Direct WebSocket {i} failed: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ Direct WebSocket error: {e}")
        return False

async def main():
    print("🧪 COMPREHENSIVE DHANHQ API TEST")
    print("=" * 60)
    
    # Test all approaches
    rest_success = await test_all_approaches()
    ws_success = await test_websocket_variations()
    direct_success = await test_direct_websocket()
    
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE RESULTS:")
    print(f"✅ REST API: {'WORKING' if rest_success else 'FAILED'}")
    print(f"✅ WebSocket (Library): {'WORKING' if ws_success else 'FAILED'}")
    print(f"✅ Direct WebSocket: {'WORKING' if direct_success else 'FAILED'}")
    
    success_count = sum([rest_success, ws_success, direct_success])
    
    if success_count > 0:
        print(f"\n🎉 SUCCESS! {success_count}/3 approaches working!")
        print("🚀 Ready for integration!")
        
        if rest_success:
            print("✅ Use REST API for historical data")
        if ws_success:
            print("✅ Use WebSocket for real-time data")
        if direct_success:
            print("✅ Use Direct WebSocket for custom implementation")
    else:
        print("\n❌ All approaches failed")
        print("🎯 Check:")
        print("1. Token validity (expires in ~11 hours)")
        print("2. API subscription status")
        print("3. Market hours (9:15 AM - 3:30 PM IST)")
        print("4. DhanHQ account status")

if __name__ == "__main__":
    asyncio.run(main())
