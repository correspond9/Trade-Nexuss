#!/usr/bin/env python3
"""
Check the DhanHQ token from database
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the fastapi-backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi-backend'))

def decode_jwt_token(token):
    """Decode JWT token without verification"""
    try:
        import base64
        import json
        import datetime
        
        # Remove Bearer prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Split token into parts
        parts = token.split('.')
        
        if len(parts) != 3:
            print("❌ Invalid JWT format - should have 3 parts")
            return None
        
        # Decode header
        header = base64.urlsafe_b64decode(parts[0] + '==')
        header_data = json.loads(header)
        
        # Decode payload
        payload = base64.urlsafe_b64decode(parts[1] + '==')
        payload_data = json.loads(payload)
        
        return {
            'header': header_data,
            'payload': payload_data,
            'signature': parts[2]
        }
        
    except Exception as e:
        print(f"❌ Error decoding token: {e}")
        return None

def check_database_token():
    """Check token from database"""
    print("🔍 Checking Database Token")
    print("=" * 30)
    
    try:
        from app.services.credential_manager import get_dhan_credentials
        
        credentials = get_dhan_credentials()
        
        if credentials['mode'] == 'DAILY_TOKEN':
            token = credentials['access_token']
            print(f"📝 Token (first 20 chars): {token[:20]}...")
            print(f"📏 Token length: {len(token)} characters")
            
            # Decode token
            decoded = decode_jwt_token(token)
            
            if decoded:
                print("\n📋 Token Header:")
                for key, value in decoded['header'].items():
                    print(f"  {key}: {value}")
                
                print("\n📋 Token Payload:")
                for key, value in decoded['payload'].items():
                    if key == 'exp':
                        import datetime
                        expiry_date = datetime.datetime.fromtimestamp(value)
                        now = datetime.datetime.now()
                        is_expired = now > expiry_date
                        status = "❌ EXPIRED" if is_expired else "✅ VALID"
                        print(f"  {key}: {value} ({expiry_date.strftime('%Y-%m-%d %H:%M:%S')}) {status}")
                    else:
                        print(f"  {key}: {value}")
                
                # Check expiry
                if 'exp' in decoded['payload']:
                    import datetime
                    expiry_timestamp = decoded['payload']['exp']
                    expiry_date = datetime.datetime.fromtimestamp(expiry_timestamp)
                    now = datetime.datetime.now()
                    
                    if now > expiry_date:
                        print(f"\n❌ TOKEN EXPIRED!")
                        print(f"   Expired on: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"   Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                        return False
                    else:
                        time_left = expiry_date - now
                        print(f"\n✅ TOKEN VALID!")
                        print(f"   Expires on: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"   Time left: {time_left}")
                        
                        # Check client ID
                        client_id = decoded['payload'].get('dhanClientId')
                        print(f"\n🆔 Client ID from token: {client_id}")
                        
                        if client_id == '1100353799':
                            print("✅ Client ID matches your live account!")
                        else:
                            print(f"⚠️  Client ID mismatch. Expected: 1100353799, Got: {client_id}")
                        
                        return True
                else:
                    print("\n⚠️  No expiry date found in token")
                    return None
        else:
            print(f"❌ Not using daily token mode: {credentials['mode']}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_database_token()
