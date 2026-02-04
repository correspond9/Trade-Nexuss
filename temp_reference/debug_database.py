#!/usr/bin/env python3
"""
Debug database connection and credentials
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the fastapi-backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi-backend'))

from sqlalchemy import create_engine, text

def debug_database():
    """Debug database connection and credentials"""
    print("🔍 Database Debug Tool")
    print("=" * 30)
    
    # Check environment
    database_url = os.getenv('DATABASE_URL')
    print(f"📊 DATABASE_URL from env: {database_url}")
    
    # Test credential manager
    try:
        from app.services.credential_manager import get_credential_manager
        
        manager = get_credential_manager()
        print(f"📊 Manager database URL: {manager.database_url}")
        
        # Test connection
        with manager.engine.connect() as conn:
            print("✅ Database connected successfully")
            
            # List all tables
            tables = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table'
            """)).fetchall()
            
            print(f"📋 All tables: {[t[0] for t in tables]}")
            
            # Check Dhan tables
            dhan_tables = [t[0] for t in tables if 'dhan' in t[0].lower()]
            print(f"📋 Dhan tables: {dhan_tables}")
            
            if dhan_tables:
                # Check auth mode
                try:
                    auth_mode = conn.execute(text("""
                        SELECT mode FROM dhan_auth_mode 
                        WHERE is_active = 1 
                        ORDER BY last_switched_at DESC 
                        LIMIT 1
                    """)).fetchone()
                    
                    print(f"🔐 Active auth mode: {auth_mode}")
                    
                    if auth_mode and auth_mode[0] == 'DAILY_TOKEN':
                        token = conn.execute(text("""
                            SELECT access_token FROM dhan_daily_token_credentials 
                            WHERE is_active = 1
                            ORDER BY generated_at DESC 
                            LIMIT 1
                        """)).fetchone()
                        
                        if token:
                            print(f"📝 Token found: {token[0][:20]}...")
                        else:
                            print("❌ No active token found")
                    
                except Exception as e:
                    print(f"❌ Error checking credentials: {e}")
            else:
                print("❌ No Dhan tables found")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_database()
