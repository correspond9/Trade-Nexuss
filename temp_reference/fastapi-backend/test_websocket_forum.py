#!/usr/bin/env python3
"""
WebSocket Connection Test - Using Official DhanHQ Library Pattern
Based on forum solutions that actually work
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_with_dhan_library():
    """Test using the official DhanHQ library pattern from forum"""
    
    try:
        # Try to import the official library (forum solution)
        from dhanhq import DhanContext, MarketFeed
        
        print("📚 Using Official DhanHQ Library (Forum Solution)")
        print("=" * 50)
        
        # Test credentials (forum pattern)
        client_id = "1100353799"
        access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"
        
        print(f"🔑 Client ID: {client_id}")
        print(f"🎫 Token: {access_token[:20]}...")
        
        # Create DhanContext (forum pattern)
        dhan_context = DhanContext(client_id, access_token.strip())
        
        # Define instruments (forum pattern)
        instruments = [
            ("NSE", "13626", "Ticker"),  # NIFTY
            ("NSE", "14152", "Ticker"),  # BANKNIFTY
        ]
        
        version = "v2"
        
        print(f"📡 Creating MarketFeed with {len(instruments)} instruments...")
        
        # Create MarketFeed (forum pattern)
        data = MarketFeed(dhan_context, instruments, version)
        
        try:
            print("🔌 Connecting to Dhan MarketFeed...")
            await data.connect()
            print("✅ Connected successfully!")
            
            # Subscribe to instruments (forum pattern)
            print("📤 Subscribing to instruments...")
            await data.subscribe_symbols(instruments)
            print("✅ Subscribed successfully!")
            
            # Test data reception (forum pattern)
            print("📊 Testing data reception...")
            for i in range(3):
                try:
                    response = data.get_data()
                    print(f"📨 Data {i+1}: {response}")
                    if 'LTP' in response:
                        print(f"💰 LTP: {response['LTP']}")
                except Exception as e:
                    print(f"⏰ No data available (market hours?): {e}")
                await asyncio.sleep(2)
            
            print("✅ Test completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ MarketFeed error: {e}")
            if "429" in str(e):
                print("🚨 HTTP 429: Rate limiting (forum issue)")
            elif "1006" in str(e):
                print("🚨 WebSocket Error 1006 (forum issue)")
            return False
        finally:
            await data.disconnect()
            print("🔌 Disconnected")
            
    except ImportError as e:
        print(f"❌ DhanHQ library not available: {e}")
        print("💡 Install with: pip install dhanhq")
        return False
    except Exception as e:
        print(f"❌ Library error: {e}")
        return False

async def test_alternative_approach():
    """Test alternative approach from forum - direct WebSocket with proper headers"""
    
    print("\n🔄 Alternative Approach (Forum Pattern)")
    print("=" * 50)
    
    try:
        import websockets
        
        # Forum suggests trying different endpoint formats
        endpoints_to_test = [
            "wss://api-feed.dhan.co?version=2&token=test&clientId=1100353799&authType=2",
            "wss://api-feed.dhan.co?version=2&token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test&clientId=1100353799&authType=2",
            "wss://api-feed.dhan.co?version=2&token=invalid&clientId=1100353799&authType=2",
        ]
        
        for i, endpoint in enumerate(endpoints_to_test, 1):
            print(f"\n🧪 Endpoint Test {i}:")
            print(f"📡 {endpoint}")
            
            try:
                websocket = await websockets.connect(
                    endpoint,
                    ping_interval=20,
                    ping_timeout=10,
                    extra_headers={
                        "User-Agent": "DhanHQ-WebSocket-Test/1.0"
                    }
                )
                
                print(f"✅ Endpoint {i}: Connected!")
                
                # Try to keep connection alive
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    print(f"📨 Endpoint {i}: Received data!")
                except asyncio.TimeoutError:
                    print(f"⏰ Endpoint {i}: No data (but connected)")
                
                await websocket.close()
                return True
                
            except Exception as e:
                print(f"❌ Endpoint {i} failed: {e}")
    
    except Exception as e:
        print(f"❌ Alternative approach failed: {e}")
    
    return False

async def main():
    print("🧪 DhanHQ WebSocket Forum Solutions Test")
    print("=" * 60)
    
    # Test 1: Official library (forum solution)
    success1 = await test_with_dhan_library()
    
    # Test 2: Alternative approaches
    success2 = await test_alternative_approach()
    
    if success1 or success2:
        print("\n✅ At least one solution worked!")
        print("🎯 Next steps:")
        print("1. Use the working approach in production")
        print("2. Get real DhanHQ credentials")
        print("3. Test during market hours")
    else:
        print("\n❌ All solutions failed")
        print("🎯 Forum recommendations:")
        print("1. Check DhanHQ account status")
        print("2. Verify API subscription")
        print("3. Contact DhanHQ support")
        print("4. Consider alternative brokers")

if __name__ == "__main__":
    asyncio.run(main())
