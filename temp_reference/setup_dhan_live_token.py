#!/usr/bin/env python3
"""
Script to generate new DhanHQ access token for live client ID
"""
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_dhan_token():
    """Generate new access token for DhanHQ"""
    print("🔑 DhanHQ Token Generator")
    print("=" * 40)
    
    # Get credentials
    client_id = os.getenv('DHAN_CLIENT_ID')
    api_key = os.getenv('BROKER_API_KEY')
    api_secret = os.getenv('BROKER_API_SECRET')
    
    print(f"📋 Client ID: {client_id}")
    print(f"📋 API Key: {'Configured' if api_key else 'Not configured'}")
    print(f"📋 API Secret: {'Configured' if api_secret else 'Not configured'}")
    
    if not all([client_id, api_key, api_secret]):
        print("\n❌ Missing credentials!")
        print("Please ensure the following are set in .env:")
        print("- DHAN_CLIENT_ID=1100353799")
        print("- BROKER_API_KEY=your_live_api_key")
        print("- BROKER_API_SECRET=your_live_api_secret")
        return False
    
    # DhanHQ API endpoints
    base_url = "https://api.dhan.co"
    
    try:
        print(f"\n🔌 Connecting to DhanHQ API...")
        
        # Prepare headers
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-API-KEY': api_key,
            'X-CLIENT-ID': client_id,
            'X-API-SIGNATURE': generate_signature(api_secret)
        }
        
        print(f"📤 Making request to: {base_url}/oauth/token")
        
        # Generate token request
        response = requests.post(
            f"{base_url}/oauth/token",
            headers=headers,
            json={
                "grant_type": "client_credentials"
            },
            timeout=30
        )
        
        print(f"📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            
            if 'access_token' in token_data:
                access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 86400)
                
                print(f"✅ Token generated successfully!")
                print(f"📝 Token (first 20 chars): {access_token[:20]}...")
                print(f"⏰ Expires in: {expires_in} seconds")
                
                # Save token to .env file
                save_token_to_env(access_token)
                
                return True
            else:
                print(f"❌ No access token in response: {token_data}")
                return False
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def generate_signature(api_secret):
    """Generate signature for DhanHQ API (simplified)"""
    # This is a placeholder - actual signature generation may be different
    # You might need to check DhanHQ documentation for exact signature method
    import hashlib
    import hmac
    import time
    
    timestamp = str(int(time.time()))
    message = timestamp
    
    signature = hmac.new(
        api_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature

def save_token_to_env(access_token):
    """Save new token to .env file"""
    try:
        env_file = '.env'
        
        # Read current .env
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Replace the token line
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.startswith('DHAN_ACCESS_TOKEN='):
                updated_lines.append(f'DHAN_ACCESS_TOKEN={access_token}')
            else:
                updated_lines.append(line)
        
        # Write back to .env
        with open(env_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        print(f"✅ Token saved to .env file")
        
    except Exception as e:
        print(f"❌ Error saving token: {e}")
        print(f"Please manually update .env with:")
        print(f"DHAN_ACCESS_TOKEN={access_token}")

def manual_token_entry():
    """Allow manual token entry"""
    print("\n📝 Manual Token Entry")
    print("=" * 30)
    print("If you have a token from DhanHQ dashboard,")
    print("please enter it below:")
    
    token = input("Enter Access Token: ").strip()
    
    if token and len(token) > 50:
        save_token_to_env(token)
        return True
    else:
        print("❌ Invalid token format")
        return False

def main():
    """Main function"""
    print("🚀 DhanHQ Live Token Setup")
    print("=" * 50)
    print("This will help you set up the correct token for client ID 1100353799")
    print()
    
    choice = input("Choose option:\n1. Generate new token (requires API credentials)\n2. Enter token manually\nChoice (1/2): ").strip()
    
    if choice == '1':
        success = generate_dhan_token()
    elif choice == '2':
        success = manual_token_entry()
    else:
        print("❌ Invalid choice")
        return
    
    if success:
        print("\n🎉 Token setup completed!")
        print("You can now test the WebSocket connection:")
        print("python debug_dhan_websocket.py")
    else:
        print("\n❌ Token setup failed!")
        print("Please check your credentials and try again")

if __name__ == "__main__":
    main()
