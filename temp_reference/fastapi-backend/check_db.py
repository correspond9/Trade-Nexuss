import sqlite3
import os

def check_database():
    db_path = 'databases/trading_terminal.db'
    
    if os.path.exists(db_path):
        print(f"✅ Database file found: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"\n📊 Tables in database ({len(tables)} total):")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check credentials table structure
        if ('dhan_credentials',) in tables:
            print(f"\n🔐 DhanCredentials table structure:")
            cursor.execute('PRAGMA table_info(dhan_credentials);')
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
                
            # Check for existing data
            cursor.execute('SELECT COUNT(*) FROM dhan_credentials;')
            count = cursor.fetchone()[0]
            print(f"\n📈 Existing credentials count: {count}")
            
            if count > 0:
                cursor.execute('SELECT id, user_id, auth_mode, is_default, created_at FROM dhan_credentials;')
                rows = cursor.fetchall()
                print("📋 Existing credentials:")
                for row in rows:
                    print(f"  - ID: {row[0]}, User: {row[1]}, Mode: {row[2]}, Default: {row[3]}, Created: {row[4]}")
        else:
            print("\n❌ dhan_credentials table not found!")
        
        # Check credential_logs table
        if ('credential_logs',) in tables:
            print(f"\n📝 CredentialLogs table structure:")
            cursor.execute('PRAGMA table_info(credential_logs);')
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
                
            cursor.execute('SELECT COUNT(*) FROM credential_logs;')
            count = cursor.fetchone()[0]
            print(f"\n📈 Existing logs count: {count}")
        
        conn.close()
    else:
        print(f"❌ Database file does not exist: {db_path}")

if __name__ == "__main__":
    check_database()
