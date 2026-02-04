#!/usr/bin/env python
"""
Simple test script to verify backend is running and serving price data
"""
import sys
import time
import requests
import json

def test_prices_endpoint():
    """Test the /prices endpoint"""
    max_retries = 5
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"\n[Attempt {attempt + 1}/{max_retries}] Testing /prices endpoint...")
            response = requests.get('http://127.0.0.1:8000/prices', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"[SUCCESS] Status: {response.status_code}")
                print(f"[DATA] Live Prices:\n{json.dumps(data, indent=2)}")
                return True
            else:
                print(f"[ERROR] Status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] Connection refused. Backend may not be ready...")
            if attempt < max_retries - 1:
                print(f"[WAIT] Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            if attempt < max_retries - 1:
                print(f"[WAIT] Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    
    return False

def test_health_endpoint():
    """Test the /health endpoint"""
    try:
        print("\n[Test] Checking /health endpoint...")
        response = requests.get('http://127.0.0.1:8000/health', timeout=5)
        print(f"[Health] Status: {response.status_code}")
        if response.status_code == 200:
            print(f"[Health] Data: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"[Health Error] {str(e)}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Live Prices Backend Test")
    print("=" * 60)
    
    # Test health first
    if test_health_endpoint():
        print("\n[INFO] Backend is healthy!")
    else:
        print("\n[WARN] Backend health check failed")
    
    # Test prices
    if test_prices_endpoint():
        print("\n[SUCCESS] Backend is serving price data!")
        sys.exit(0)
    else:
        print("\n[FAILED] Could not connect to backend")
        sys.exit(1)
