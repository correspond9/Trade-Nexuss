import requests
import json

def test_credentials_api():
    base_url = "http://127.0.0.1:5000/api/v1"
    
    print("🧪 Testing Credentials API...")
    
    # Test 1: Get active mode
    try:
        response = requests.get(f"{base_url}/credentials/active")
        print(f"✅ GET /credentials/active: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ GET /credentials/active failed: {e}")
    
    # Test 2: Save credentials
    try:
        payload = {
            "auth_mode": "DAILY_TOKEN",
            "client_id": "1100353799",
            "access_token": "test_token_123",
            "is_default": True
        }
        response = requests.post(f"{base_url}/credentials", json=payload)
        print(f"✅ POST /credentials: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ POST /credentials failed: {e}")
    
    # Test 3: Get credentials after save
    try:
        response = requests.get(f"{base_url}/credentials?auth_mode=DAILY_TOKEN")
        print(f"✅ GET /credentials?auth_mode=DAILY_TOKEN: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ GET /credentials failed: {e}")
    
    # Test 4: Switch mode
    try:
        payload = {"auth_mode": "DAILY_TOKEN"}
        response = requests.post(f"{base_url}/credentials/switch-mode", json=payload)
        print(f"✅ POST /credentials/switch-mode: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ POST /credentials/switch-mode failed: {e}")

if __name__ == "__main__":
    test_credentials_api()
