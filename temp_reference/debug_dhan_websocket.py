#!/usr/bin/env python3
"""
Debug script to test DhanHQ WebSocket connection and data flow
Uses database admin panel credentials (overrides all other sources)
"""
import asyncio
import sys
import os
import logging
from dotenv import load_dotenv

# Load environment variables for database URL
load_dotenv()

# Add the fastapi-backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi-backend'))

from app.services.dhan_websocket import DhanWebSocketClient
from app.services.credential_manager import check_dhan_credentials_available, get_dhan_credentials

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_dhan_connection():
    """Test Dhan WebSocket connection with database credentials"""
    print("🔍 DhanHQ WebSocket Connection Test (Database Credentials)")
    print("=" * 60)
    
    # Check database credentials first
    print("\n📋 Checking Database Credentials...")
    if not check_dhan_credentials_available():
        print("❌ No credentials found in database admin panel!")
        print("\n🔧 To fix this:")
        print("1. Go to System Settings > Broker Configuration")
        print("2. Select DhanHQ as broker")
        print("3. Configure either:")
        print("   - Daily Token: Enter access token")
        print("   - Static IP: Enter Client ID, API Key, and API Secret")
        print("4. Save configuration")
        return False
    
    try:
        credentials = get_dhan_credentials()
        print(f"✅ Database credentials found!")
        print(f"   Mode: {credentials['mode']}")
        
        if credentials['mode'] == 'STATIC_IP':
            print(f"   Client ID: {credentials['client_id']}")
            print(f"   API Key: {credentials['api_key'][:10]}...")
        elif credentials['mode'] == 'DAILY_TOKEN':
            print(f"   Access Token: {credentials['access_token'][:10]}...")
            
    except Exception as e:
        print(f"❌ Error checking database credentials: {e}")
        return False
    
    # Create client (will automatically load from database)
    try:
        print("\n🔌 Creating Dhan WebSocket client...")
        client = DhanWebSocketClient()
        print("✅ Client created with database credentials")
        
        print(f"   Auth Mode: {client.auth_mode}")
        if client.auth_mode == 'token':
            print(f"   Token Available: {'Yes' if client.auth_token else 'No'}")
        else:
            print(f"   Client ID: {client.client_id}")
            print(f"   API Key Available: {'Yes' if client.api_key else 'No'}")
        
        print("\n🔌 Attempting to connect...")
        await client.connect()
        
        if client.is_connected:
            print("✅ WebSocket connected successfully!")
            
            # Test subscription
            print("\n📊 Testing subscription...")
            test_instruments = ["NIFTY", "RELIANCE-EQ", "13626"]
            
            await client.subscribe_instruments(test_instruments)
            print(f"✅ Subscribed to {len(test_instruments)} instruments")
            
            # Wait for data
            print("\n⏳ Waiting for market data (30 seconds)...")
            print("   Listening for real-time market data...")
            
            # Wait for data with timeout
            for i in range(30):
                await asyncio.sleep(1)
                if i % 5 == 0:
                    print(f"   Waiting... ({i}s elapsed)")
            
            print("\n🔍 Connection test completed")
            return True
        else:
            print("❌ WebSocket connection failed")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'client' in locals() and client.is_connected:
            await client.disconnect()
            print("🔌 WebSocket disconnected")

async def check_database_setup():
    """Check database and credential setup"""
    print("🔧 Database Configuration Check")
    print("=" * 50)
    
    # Check database URL
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        print(f"✅ DATABASE_URL found: {database_url[:50]}...")
    else:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    # Check database file exists for SQLite
    if 'sqlite' in database_url:
        db_path = database_url.replace('sqlite:///', '').replace('sqlite://', '')
        if os.path.exists(db_path):
            print(f"✅ Database file exists: {db_path}")
        else:
            print(f"❌ Database file not found: {db_path}")
            return False
    
    # Check credentials
    try:
        if check_dhan_credentials_available():
            print("✅ DhanHQ credentials available in database")
            credentials = get_dhan_credentials()
            print(f"   Mode: {credentials['mode']}")
            return True
        else:
            print("❌ DhanHQ credentials not found in database")
            return False
    except Exception as e:
        print(f"❌ Error checking database credentials: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 DhanHQ WebSocket Debug Tool (Database Admin Panel)")
    print("=" * 70)
    print("📋 This tool uses ONLY database admin panel credentials")
    print("📋 Environment variables and .env files are IGNORED")
    print("=" * 70)
    
    # Check database setup first
    if not await check_database_setup():
        print("\n❌ Database setup check failed!")
        print("Please fix the issues above and try again.")
        return
    
    print("\n" + "=" * 70)
    
    # Test connection
    success = await test_dhan_connection()
    
    if success:
        print("\n🎉 WebSocket test completed successfully!")
        print("   Live data feed should now be working!")
        print("   If you're still not getting data, check:")
        print("   1. Market hours (data only available during trading hours)")
        print("   2. Instrument symbols are correct")
        print("   3. Network connectivity to DhanHQ servers")
        print("   4. Rate limiting (wait 5-15 minutes if rate limited)")
    else:
        print("\n❌ WebSocket test failed!")
        print("   Please check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())
