#!/usr/bin/env python3
"""
Quick setup of DhanHQ credentials for client ID 1100353799
"""
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from sqlalchemy import create_engine, text

def setup_live_credentials():
    """Setup live DhanHQ credentials"""
    print("🚀 Setting up DhanHQ Live Credentials")
    print("=" * 40)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return False
    
    print(f"📊 Using database: {database_url}")
    
    # Your live access token (you can replace this with the actual token)
    live_access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY5NjYyMzEyLCJpYXQiOjE3Njk1NzU5MTIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMzUzNzk5In0.EY0Y7SvWchiJntUA2d4Mzx-em-MIcUMATwyXTQ_5JkRVSK6ngJvGW0FOs9yLzfZrryud8or48q031ETh96SYcw"
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            print("📊 Connected to database")
            
            # Check if tables exist, create if not
            tables = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'dhan_%'
            """)).fetchall()
            
            if not tables:
                print("🔨 Creating DhanHQ tables...")
                create_dhan_tables(conn)
            
            # Clear existing data
            conn.execute(text("UPDATE dhan_daily_token_credentials SET is_active = 0"))
            conn.execute(text("UPDATE dhan_static_ip_credentials SET is_active = 0"))
            conn.execute(text("UPDATE dhan_auth_mode SET is_active = 0"))
            
            # Insert daily token credentials
            conn.execute(text("""
                INSERT INTO dhan_daily_token_credentials 
                (access_token, generated_at, expires_at, is_active)
                VALUES (:token, :generated_at, :expires_at, 1)
            """), {
                'token': live_access_token,
                'generated_at': datetime.now(timezone.utc),
                'expires_at': datetime.now(timezone.utc)
            })
            
            # Set auth mode to DAILY_TOKEN
            conn.execute(text("""
                INSERT INTO dhan_auth_mode 
                (mode, data_authority, is_active, last_switched_at, switched_by, switch_reason)
                VALUES (:mode, 'PRIMARY', 1, :last_switched_at, 'auto_setup', 'Auto setup for live trading')
            """), {
                'mode': 'DAILY_TOKEN',
                'last_switched_at': datetime.now(timezone.utc)
            })
            
            conn.commit()
            print("✅ Live credentials setup completed!")
            print(f"🔐 Mode: DAILY_TOKEN")
            print(f"🆔 Client ID from token: 1100353799")
            print(f"📝 Token: {live_access_token[:20]}...")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_dhan_tables(conn):
    """Create DhanHQ authentication tables"""
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS dhan_auth_mode (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode VARCHAR(20) NOT NULL,
            data_authority VARCHAR(20) NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            last_switched_at DATETIME,
            switched_by VARCHAR(100),
            switch_reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS dhan_daily_token_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_token TEXT NOT NULL,
            generated_at DATETIME,
            expires_at DATETIME,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS dhan_static_ip_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id VARCHAR(50) NOT NULL,
            api_key TEXT NOT NULL,
            api_secret TEXT NOT NULL,
            last_used_at DATETIME,
            expires_at DATETIME,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))

def verify_credentials():
    """Verify the credentials were set correctly"""
    print("\n🔍 Verifying Credentials")
    print("=" * 30)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        return False
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Check auth mode
            auth_mode = conn.execute(text("""
                SELECT mode FROM dhan_auth_mode 
                WHERE is_active = 1 
                ORDER BY last_switched_at DESC 
                LIMIT 1
            """)).fetchone()
            
            if auth_mode:
                print(f"✅ Auth Mode: {auth_mode[0]}")
                
                if auth_mode[0] == "DAILY_TOKEN":
                    token = conn.execute(text("""
                        SELECT access_token, generated_at FROM dhan_daily_token_credentials 
                        WHERE is_active = 1
                        ORDER BY generated_at DESC 
                        LIMIT 1
                    """)).fetchone()
                    
                    if token:
                        print(f"✅ Token found: {token[0][:20]}...")
                        print(f"📅 Generated: {token[1]}")
                        return True
            
            print("❌ No active credentials found")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = setup_live_credentials()
    if success:
        verify_credentials()
        print("\n🎉 Ready to test WebSocket connection!")
        print("Run: python debug_dhan_websocket.py")
    else:
        print("\n❌ Setup failed!")
