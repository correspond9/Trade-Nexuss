#!/usr/bin/env python3
"""
Force Start WebSocket Feed
This script will force start the WebSocket feed with all Tier B subscriptions
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi_backend'))

from app.dhan.live_feed import start_live_feed
from app.market.subscription_manager import get_subscription_manager

def main():
    print("🚀 Force Starting WebSocket Feed...")
    print("=" * 60)
    
    # Get subscription manager
    sub_mgr = get_subscription_manager()
    stats = sub_mgr.get_ws_stats()
    
    print(f"📊 Current Status:")
    print(f"   • Total subscriptions: {stats['total_subscriptions']}")
    print(f"   • Tier B: {stats['tier_b_count']}")
    print(f"   • Tier A: {stats['tier_a_count']}")
    
    # Force start WebSocket feed
    print("\n🔌 Starting WebSocket feed...")
    try:
        start_live_feed()
        print("✅ WebSocket feed started successfully!")
        print("📡 Live data should start flowing in 10-15 seconds")
        
        # Wait and check
        import time
        time.sleep(15)
        
        # Check status
        from app.market.ws_manager import get_ws_manager
        ws_mgr = get_ws_manager()
        ws_status = ws_mgr.get_status()
        
        print(f"\n📊 WebSocket Status after 15 seconds:")
        print(f"   • Connected connections: {ws_status['connected_connections']}")
        print(f"   • Total subscriptions in WS: {ws_status['total_subscriptions']}")
        
        if ws_status['connected_connections'] > 0:
            print("✅ SUCCESS: WebSocket connections are active!")
        else:
            print("❌ ISSUE: WebSocket connections still not active")
            
    except Exception as e:
        print(f"❌ Failed to start WebSocket feed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
