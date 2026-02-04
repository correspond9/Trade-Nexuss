#!/usr/bin/env python3
"""
Quick fix to recreate DhanHQ database tables
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from sqlalchemy import create_engine, text

def fix_database_tables():
    """Fix database table structure"""
    print("🔧 Fixing DhanHQ Database Tables")
    print("=" * 40)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return False
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            print("📊 Connected to database")
            
            # Drop existing tables
            print("🗑️  Dropping existing tables...")
            conn.execute(text("DROP TABLE IF EXISTS dhan_static_ip_credentials"))
            conn.execute(text("DROP TABLE IF EXISTS dhan_daily_token_credentials")) 
            conn.execute(text("DROP TABLE IF EXISTS dhan_auth_mode"))
            
            # Create new tables
            print("🔨 Creating new tables...")
            
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
            print("✅ Tables created successfully!")
            
            # Verify tables
            tables = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'dhan_%'
            """)).fetchall()
            
            print(f"📋 Created tables: {[t[0] for t in tables]}")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_database_tables()
    if success:
        print("\n🎉 Database tables fixed!")
        print("Now run: python scripts/setup_dhan_database_credentials.py")
    else:
        print("\n❌ Failed to fix tables")
