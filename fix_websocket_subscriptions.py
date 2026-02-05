#!/usr/bin/env python3
"""
Fix WebSocket Subscription Issue
This script will restart the WebSocket feed with existing subscriptions
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi_backend'))

from app.market.subscription_manager import get_subscription_manager
from app.dhan.live_feed import start_live_feed, sync_subscriptions_with_watchlist

def main():
    print("🔧 Fixing WebSocket Subscription Issue...")
    print("=" * 60)
    
    # Get current subscription status
    sub_mgr = get_subscription_manager()
    stats = sub_mgr.get_ws_stats()
    
    print(f"📊 Current Status:")
    print(f"   • Total subscriptions: {stats['total_subscriptions']}")
    print(f"   • Tier A: {stats['tier_a_count']}")
    print(f"   • Tier B: {stats['tier_b_count']}")
    print(f"   • WS utilization: {stats['utilization_percent']:.1f}%")
    
    # Force sync subscriptions to WebSocket
    print("\n🔄 Syncing subscriptions to WebSocket...")
    sync_subscriptions_with_watchlist()
    
    # Restart WebSocket feed
    print("\n🚀 Restarting WebSocket feed...")
    try:
        start_live_feed()
        print("✅ WebSocket feed restarted successfully!")
        print("📡 Live data should start flowing in 10-15 seconds")
    except Exception as e:
        print(f"❌ Failed to restart WebSocket feed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🔍 Check live data:")
    print("   • Watch for: [PRICE] symbol = price messages")
    print("   • Check: http://localhost:8000/api/v2/subscriptions/status")
    print("   • Frontend should show live price updates")
    print("=" * 60)

if __name__ == "__main__":
    main()
