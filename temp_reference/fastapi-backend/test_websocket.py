#!/usr/bin/env python3
"""
WebSocket Connection Test - Based on DhanHQ Forum Solutions
Testing the exact patterns that work according to the forum
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """Test WebSocket connection using forum-recommended patterns"""
    
    # Test with different approaches from forum
    test_cases = [
        {
            "name": "V2 with test token",
            "client_id": "1100353799",
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test",
            "auth_type": 2
        },
        {
            "name": "V2 with empty token (test connection only)",
            "client_id": "1100353799", 
            "access_token": "test_token",
            "auth_type": 2
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        client_id = test_case['client_id']
        access_token = test_case['access_token']
        auth_type = test_case['auth_type']
        
        # Official DhanHQ V2 URL format (from forum)
        ws_url_v2 = f"wss://api-feed.dhan.co?version=2&token={access_token}&clientId={client_id}&authType={auth_type}"
        
        print(f"📡 URL: {ws_url_v2}")
        print(f"🔑 Client ID: {client_id}")
        print(f"🎫 Token: {access_token[:20]}...")
        
        try:
            logger.info(f"🔌 Attempting to connect (Test {i})...")
            websocket = await websockets.connect(
                ws_url_v2,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            logger.info(f"✅ Test {i}: Connected successfully!")
            
            # Wait for initial response (forum pattern)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"📨 Server response: {response}")
                
                # If we get here, connection is working!
                await websocket.close()
                return True
                
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Test {i}: No immediate response, but connection established")
                await websocket.close()
                return True  # Connection established, just no data
            
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"❌ Test {i} Connection closed: {e}")
            if e.code == 1006:
                logger.error(f"🚨 Test {i} Error 1006: Connection closed abnormally (forum issue)")
            elif "429" in str(e):
                logger.error(f"🚨 Test {i} HTTP 429: Rate limiting (forum issue)")
            elif "401" in str(e) or "403" in str(e):
                logger.error(f"🚨 Test {i} Authentication error: Invalid credentials")
        except Exception as e:
            logger.error(f"❌ Test {i} Connection failed: {type(e).__name__}: {e}")
            if "429" in str(e):
                logger.error(f"🚨 Test {i} HTTP 429: Rate limiting detected (forum issue)")
            elif "connection closed while reading HTTP status line" in str(e).lower():
                logger.error(f"🚨 Test {i} HTTP connection error (forum Session 5 issue)")
            elif "401" in str(e) or "403" in str(e):
                logger.error(f"🚨 Test {i} Authentication error")
    
    return False

async def main():
    print("🧪 DhanHQ WebSocket Connection Test")
    print("=" * 50)
    
    success = await test_websocket_connection()
    
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed - check forum solutions")
        print("\n📚 Forum Solutions to Try:")
        print("1. Check rate limiting (HTTP 429)")
        print("2. Verify client_id format")
        print("3. Ensure token is valid (24-hour expiry)")
        print("4. Check market hours (no data after hours)")

if __name__ == "__main__":
    asyncio.run(main())
