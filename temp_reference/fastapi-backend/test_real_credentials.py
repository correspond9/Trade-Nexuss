#!/usr/bin/env python3
"""
WebSocket Connection Test - Using REAL DhanHQ Credentials
Testing with official library and real credentials from API_cred.txt
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_with_real_credentials():
    """Test using REAL DhanHQ credentials and official library"""
    
    try:
        # Import the official library
        from dhanhq import DhanContext, MarketFeed
        
        print("🎯 Using REAL DhanHQ Credentials & Official Library")
        print("=" * 60)
        
        # REAL credentials from API_cred.txt
        client_id = "1100353799"
        access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY5ODQzNjA5LCJpYXQiOjE3Njk3NTcyMDksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMzUzNzk5In0.bKl_DpJ8ePk5EqUTD4tWcSLvwBTgCzz2bZYwYqMcKkk5T___OJxXSIHfPTEKwz-7hkduQGCMebVDyjWPAuopLg"
        
        print(f"🔑 Client ID: {client_id}")
        print(f"🎫 Token: {access_token[:50]}...")
        print(f"⏰ Token expiry: Check if valid (looks like JWT with exp)")
        
        # Create DhanContext (official pattern)
        dhan_context = DhanContext(client_id, access_token.strip())
        
        # Define instruments (forum pattern)
        instruments = [
            ("NSE", "13626", "Ticker"),  # NIFTY
            ("NSE", "14152", "Ticker"),  # BANKNIFTY
            ("NSE", "265", "Ticker"),    # SENSEX
        ]
        
        version = "v2"
        
        print(f"📡 Creating MarketFeed with {len(instruments)} instruments...")
        print(f"📊 Instruments: {[inst[1] for inst in instruments]}")
        
        # Create MarketFeed (official pattern)
        data = MarketFeed(dhan_context, instruments, version)
        
        try:
            print("🔌 Connecting to Dhan MarketFeed...")
            await data.connect()
            print("✅ Connected successfully!")
            
            # Subscribe to instruments (official pattern)
            print("📤 Subscribing to instruments...")
            await data.subscribe_symbols(instruments)
            print("✅ Subscribed successfully!")
            
            # Test data reception (official pattern)
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
            print(f"❌ MarketFeed error: {e}")
            if "429" in str(e):
                print("🚨 HTTP 429: Rate limiting")
            elif "1006" in str(e):
                print("🚨 WebSocket Error 1006")
            elif "401" in str(e) or "403" in str(e):
                print("🚨 Authentication error - check token expiry")
            elif "404" in str(e):
                print("🚨 Invalid endpoint or instrument")
            else:
                print(f"🚨 Other error: {type(e).__name__}")
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

async def test_token_validity():
    """Test if the token is valid and not expired"""
    
    print("\n🔍 Token Validity Check")
    print("=" * 30)
    
    try:
        import base64
        import json
        from datetime import datetime
        
        token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY5ODQzNjA5LCJpYXQiOjE3Njk3NTcyMDksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMzUzNzk5In0.bKl_DpJ8ePk5EqUTD4tWcSLvwBTgCzz2bZYwYqMcKkk5T___OJxXSIHfPTEKwz-7hkduQGCMebVDyjWPAuopLg"
        
        # Decode JWT payload
        parts = token.split('.')
        if len(parts) >= 2:
            payload = base64.urlsafe_b64decode(parts[1] + '==')
            token_data = json.loads(payload)
            
            exp_timestamp = token_data.get('exp')
            iat_timestamp = token_data.get('iat')
            
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                iat_datetime = datetime.fromtimestamp(iat_timestamp)
                current_time = datetime.now()
                
                print(f"📅 Issued At: {iat_datetime}")
                print(f"⏰ Expires At: {exp_datetime}")
                print(f"🕐 Current Time: {current_time}")
                
                if current_time < exp_datetime:
                    time_left = exp_datetime - current_time
                    print(f"✅ Token Valid! Time left: {time_left}")
                    return True
                else:
                    print(f"❌ Token Expired! Expired: {exp_datetime}")
                    return False
            else:
                print("⚠️  No expiry info in token")
                return False
        else:
            print("❌ Invalid token format")
            return False
            
    except Exception as e:
        print(f"❌ Token validation error: {e}")
        return False

async def main():
    print("🧪 DhanHQ WebSocket - REAL Credentials Test")
    print("=" * 70)
    
    # First check token validity
    token_valid = await test_token_validity()
    
    if not token_valid:
        print("\n❌ Token is expired or invalid!")
        print("💡 Get a new token from DhanHQ dashboard")
        return
    
    # Test with real credentials
    success = await test_with_real_credentials()
    
    if success:
        print("\n🎉 SUCCESS! WebSocket connection works with real credentials!")
        print("🎯 Ready to integrate into our application!")
    else:
        print("\n❌ Connection failed with real credentials")
        print("🎯 Check:")
        print("1. DhanHQ account status")
        print("2. API subscription active")
        print("3. Market hours (9:15 AM - 3:30 PM IST)")

if __name__ == "__main__":
    asyncio.run(main())
