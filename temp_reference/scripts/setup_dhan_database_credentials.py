#!/usr/bin/env python3
"""
Setup DhanHQ credentials in database admin panel
This script helps configure credentials for the centralized system
"""
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the fastapi-backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi-backend'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def setup_dhan_credentials():
    """Setup DhanHQ credentials in database"""
    print("🔧 DhanHQ Database Credential Setup")
    print("=" * 50)
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    print(f"📊 Database: {database_url[:50]}...")
    
    try:
        # Create database connection
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={'check_same_thread': False} if 'sqlite' in database_url else {}
        )
        
        with engine.connect() as conn:
            print("✅ Database connected successfully")
            
            # Check if tables exist
            tables = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'dhan_%'
            """)).fetchall() if 'sqlite' in database_url else []
            
            if not tables:
                print("❌ DhanHQ tables not found. Creating tables...")
                create_dhan_tables(conn)
            
            print("\n📋 Choose authentication mode:")
            print("1. Daily Token (Access Token)")
            print("2. Static IP (Client ID, API Key, API Secret)")
            
            choice = input("\nEnter choice (1 or 2): ").strip()
            
            if choice == '1':
                return setup_daily_token_credentials(conn)
            elif choice == '2':
                return setup_static_ip_credentials(conn)
            else:
                print("❌ Invalid choice")
                return False
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def create_dhan_tables(conn):
    """Create DhanHQ authentication tables"""
    print("🔨 Creating DhanHQ authentication tables...")
    
    # Drop existing tables to recreate with correct structure
    conn.execute(text("DROP TABLE IF EXISTS dhan_static_ip_credentials"))
    conn.execute(text("DROP TABLE IF EXISTS dhan_daily_token_credentials"))
    conn.execute(text("DROP TABLE IF EXISTS dhan_auth_mode"))
    
    # Create tables with correct structure
    conn.execute(text("""
        CREATE TABLE dhan_auth_mode (
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
        CREATE TABLE dhan_daily_token_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_token TEXT NOT NULL,
            generated_at DATETIME,
            expires_at DATETIME,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE dhan_static_ip_credentials (
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
    
    conn.commit()
    print("✅ Tables created successfully")

def setup_daily_token_credentials(conn):
    """Setup daily token credentials"""
    print("\n🔑 Daily Token Configuration")
    print("-" * 30)
    
    access_token = input("Enter Access Token: ").strip()
    
    if not access_token or len(access_token) < 50:
        print("❌ Invalid access token format")
        return False
    
    # Clear existing daily token credentials
    conn.execute(text("UPDATE dhan_daily_token_credentials SET is_active = 0"))
    
    # Insert new credentials
    conn.execute(text("""
        INSERT INTO dhan_daily_token_credentials 
        (access_token, generated_at, expires_at, is_active)
        VALUES (:token, :generated_at, :expires_at, 1)
    """), {
        'token': access_token,
        'generated_at': datetime.now(timezone.utc),
        'expires_at': datetime.now(timezone.utc)
    })
    
    # Set auth mode
    set_auth_mode(conn, 'DAILY_TOKEN', 'Daily token configured via setup script')
    
    conn.commit()
    print("✅ Daily token credentials saved to database")
    return True

def setup_static_ip_credentials(conn):
    """Setup static IP credentials"""
    print("\n🔐 Static IP Configuration")
    print("-" * 25)
    
    client_id = input("Enter Client ID: ").strip()
    api_key = input("Enter API Key: ").strip()
    api_secret = input("Enter API Secret: ").strip()
    
    if not all([client_id, api_key, api_secret]):
        print("❌ All fields are required")
        return False
    
    # Clear existing static IP credentials
    conn.execute(text("UPDATE dhan_static_ip_credentials SET is_active = 0"))
    
    # Insert new credentials
    conn.execute(text("""
        INSERT INTO dhan_static_ip_credentials 
        (client_id, api_key, api_secret, last_used_at, is_active)
        VALUES (:client_id, :api_key, :api_secret, :last_used_at, 1)
    """), {
        'client_id': client_id,
        'api_key': api_key,
        'api_secret': api_secret,
        'last_used_at': datetime.now(timezone.utc)
    })
    
    # Set auth mode
    set_auth_mode(conn, 'STATIC_IP', 'Static IP configured via setup script')
    
    conn.commit()
    print("✅ Static IP credentials saved to database")
    return True

def set_auth_mode(conn, mode, reason):
    """Set the active authentication mode"""
    # Clear existing auth modes
    conn.execute(text("UPDATE dhan_auth_mode SET is_active = 0"))
    
    # Insert new auth mode
    conn.execute(text("""
        INSERT INTO dhan_auth_mode 
        (mode, data_authority, is_active, last_switched_at, switched_by, switch_reason)
        VALUES (:mode, 'PRIMARY', 1, :last_switched_at, 'setup_script', :reason)
    """), {
        'mode': mode,
        'last_switched_at': datetime.now(timezone.utc),
        'reason': reason
    })

def view_current_credentials():
    """View current credentials in database"""
    print("📋 Current Database Credentials")
    print("=" * 40)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Get current auth mode
            auth_mode = conn.execute(text("""
                SELECT mode FROM dhan_auth_mode 
                WHERE is_active = 1 
                ORDER BY last_switched_at DESC 
                LIMIT 1
            """)).fetchone()
            
            if not auth_mode:
                print("❌ No authentication mode configured")
                return
            
            mode = auth_mode[0]
            print(f"🔐 Current Mode: {mode}")
            
            if mode == "DAILY_TOKEN":
                token = conn.execute(text("""
                    SELECT access_token, generated_at, expires_at
                    FROM dhan_daily_token_credentials 
                    WHERE is_active = 1
                    ORDER BY generated_at DESC 
                    LIMIT 1
                """)).fetchone()
                
                if token:
                    print(f"📝 Access Token: {token[0][:20]}...")
                    print(f"📅 Generated: {token[1]}")
                    print(f"⏰ Expires: {token[2]}")
                    
            elif mode == "STATIC_IP":
                creds = conn.execute(text("""
                    SELECT client_id, api_key, last_used_at
                    FROM dhan_static_ip_credentials 
                    WHERE is_active = 1
                    ORDER BY last_used_at DESC 
                    LIMIT 1
                """)).fetchone()
                
                if creds:
                    print(f"🆔 Client ID: {creds[0]}")
                    print(f"🔑 API Key: {creds[1][:20]}...")
                    print(f"📅 Last Used: {creds[2]}")
            
            print("✅ Credentials configured in database")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main function"""
    print("🚀 DhanHQ Credential Management System")
    print("=" * 50)
    print("This tool manages DhanHQ credentials in the database admin panel")
    print("Environment variables and .env files are IGNORED")
    print("=" * 50)
    
    choice = input("\nChoose option:\n1. Setup new credentials\n2. View current credentials\n3. Exit\nChoice (1/2/3): ").strip()
    
    if choice == '1':
        success = setup_dhan_credentials()
        if success:
            print("\n🎉 Credentials setup completed!")
            print("You can now test the WebSocket connection:")
            print("python debug_dhan_websocket.py")
        else:
            print("\n❌ Setup failed!")
            
    elif choice == '2':
        view_current_credentials()
        
    elif choice == '3':
        print("👋 Goodbye!")
        
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
