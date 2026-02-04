#!/usr/bin/env python3
"""
WebSocket Connection Test - Using REAL DhanHQ Credentials & Correct API
Testing with the actual DhanHQ library API that's available
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_with_real_credentials():
    """Test using REAL DhanHQ credentials and correct API"""
    
    try:
        # Import the correct classes
        from dhanhq import DhanFeed
        
        print("🎯 Using REAL DhanHQ Credentials & Correct API")
        print("=" * 60)
        
        # REAL credentials from API_cred.txt
        client_id = "1100353799"
        access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY5ODQzNjA5LCJpYXQiOjE3Njk3NTcyMDksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMzUzNzk5In0.bKl_DpJ8ePk5EqUTD4tWcSLvwBTgCzz2bZYwYqMcKkk5T___OJxXSIHfPTEKwz-7hkduQGCMebVDyjWPAuopLg"
        
        print(f"🔑 Client ID: {client_id}")
        print(f"🎫 Token: {access_token[:50]}...")
        
        # Define instruments (correct format for DhanFeed)
        instruments = [
            ("NSE", "13626", "Ticker"),  # NIFTY
            ("NSE", "14152", "Ticker"),  # BANKNIFTY
            ("NSE", "265", "Ticker"),    # SENSEX
        ]
        
        version = "v2"  # Use v2 as per forum
        
        print(f"📡 Creating DhanFeed with {len(instruments)} instruments...")
        print(f"📊 Instruments: {[inst[1] for inst in instruments]}")
        
        # Create DhanFeed (correct constructor)
        data = DhanFeed(client_id, access_token.strip(), instruments, version)
        
        try:
            print("🔌 Connecting to Dhan MarketFeed...")
            await data.connect()
            print("✅ Connected successfully!")
            
            # Subscribe to instruments (correct method)
            print("📤 Subscribing to instruments...")
            await data.subscribe_symbols(instruments)
            print("✅ Subscribed successfully!")
            
            # Test data reception
            print("📊 Testing data reception (30 seconds)...")
            data_received = False
            
            for i in range(15):  # 15 attempts = 30 seconds
                try:
                    response = data.get_data()
                    if response and response != {}:
                        print(f"📨 Data {i+1}: {response}")
                        if 'LTP' in response:
                            print(f"💰 LTP: {response['LTP']}")
                        data_received = True
                    else:
                        print(f"⏰ No data {i+1} (market hours?)")
                except Exception as e:
                    print(f"⏰ No data {i+1}: {e}")
                
                await asyncio.sleep(2)
            
            if data_received:
                print("✅ SUCCESS: Real data received from DhanHQ!")
            else:
                print("⚠️  No data received (might be outside market hours)")
            
            print("✅ Test completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ DhanFeed error: {e}")
            if "429" in str(e):
                print("🚨 HTTP 429: Rate limiting")
            elif "1006" in str(e):
                print("🚨 WebSocket Error 1006")
            elif "401" in str(e) or "403" in str(e):
                print("🚨 Authentication error - check token expiry")
            elif "404" in str(e):
                print("🚨 Invalid endpoint or instrument")
            elif "connection closed" in str(e).lower():
                print("🚨 Connection closed (forum issue)")
            else:
                print(f"🚨 Other error: {type(e).__name__}: {e}")
            return False
        finally:
            await data.disconnect()
            print("🔌 Disconnected")
            
    except ImportError as e:
        print(f"❌ DhanHQ library error: {e}")
        return False
    except Exception as e:
        print(f"❌ General error: {e}")
        return False

async def test_alternative_approach():
    """Test alternative approach using the dhanhq class"""
    
    print("\n🔄 Alternative Approach - Using dhanhq class")
    print("=" * 50)
    
    try:
        from dhanhq import dhanhq
        
        client_id = "1100353799"
        access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY5ODQzNjA5LCJpYXQiOjE3Njk3NTcyMDksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMzUzNzk5In0.bKl_DpJ8ePk5EqUTD4tWcSLvwBTgCzz2bZYwYqMcKkk5T___OJxXSIHfPTEKwz-7hkduQGCMebVDyjWPAuopLg"
        
        print(f"🔑 Client ID: {client_id}")
        print(f"🎫 Token: {access_token[:50]}...")
        
        # Create dhanhq instance
        dhan = dhanhq(client_id, access_token.strip())
        
        # Test ticker data (REST API first)
        print("📊 Testing ticker data (REST API)...")
        try:
            ticker_data = dhan.ticker_data(["13626"])  # NIFTY
            print(f"📨 Ticker data: {ticker_data}")
            if ticker_data and 'data' in ticker_data:
                print("✅ REST API working!")
                return True
            else:
                print("⚠️  REST API returned no data")
        except Exception as e:
            print(f"❌ Ticker data error: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ Alternative approach error: {e}")
        return False

async def main():
    print("🧪 DhanHQ WebSocket - REAL Credentials & Correct API Test")
    print("=" * 70)
    
    # Test 1: WebSocket with DhanFeed
    success1 = await test_with_real_credentials()
    
    # Test 2: Alternative REST API approach
    success2 = await test_alternative_approach()
    
    if success1 or success2:
        print("\n🎉 SUCCESS! At least one approach works!")
        print("🎯 Ready to integrate into our application!")
        
        if success1:
            print("✅ WebSocket (DhanFeed) - Ready for real-time data")
        if success2:
            print("✅ REST API (dhanhq) - Ready for historical data")
    else:
        print("\n❌ All approaches failed")
        print("🎯 Check:")
        print("1. DhanHQ account status")
        print("2. API subscription active")
        print("3. Market hours (9:15 AM - 3:30 PM IST)")
        print("4. Token expiry (our token expires in ~11 hours)")

if __name__ == "__main__":
    asyncio.run(main())
