#!/usr/bin/env python3
"""
Quick script to decode JWT token and check expiry
"""
import base64
import json
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def decode_jwt_token(token):
    """Decode JWT token without verification"""
    try:
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

def check_token_expiry():
    """Check if Dhan token is expired"""
    print("🔍 DhanHQ Token Analysis")
    print("=" * 40)
    
    access_token = os.getenv('DHAN_ACCESS_TOKEN')
    
    if not access_token:
        print("❌ DHAN_ACCESS_TOKEN not found in environment")
        return False
    
    print(f"📝 Token (first 20 chars): {access_token[:20]}...")
    print(f"📏 Token length: {len(access_token)} characters")
    
    # Decode token
    decoded = decode_jwt_token(access_token)
    
    if not decoded:
        return False
    
    print("\n📋 Token Header:")
    for key, value in decoded['header'].items():
        print(f"  {key}: {value}")
    
    print("\n📋 Token Payload:")
    for key, value in decoded['payload'].items():
        if key == 'exp':
            # Convert timestamp to readable date
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
            return True
    else:
        print("\n⚠️  No expiry date found in token")
        return None

if __name__ == "__main__":
    check_token_expiry()
