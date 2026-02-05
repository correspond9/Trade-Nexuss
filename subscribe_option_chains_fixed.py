#!/usr/bin/env python3
"""
Subscribe Option Chain Skeletons to WebSocket - Fixed Version
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi_backend'))

from app.services.authoritative_option_chain_service import authoritative_option_chain_service
from app.market.subscription_manager import get_subscription_manager

def main():
    print('🔧 Subscribing Option Chain Skeletons to WebSocket...')
    print('=' * 60)

    # Get option chain cache statistics
    stats = authoritative_option_chain_service.get_cache_statistics()
    print('📊 Option Chain Cache Stats:')
    print('   • Underlyings: {}'.format(stats['total_underlyings']))
    print('   • Expiries: {}'.format(stats['total_expiries']))
    print('   • Strikes: {}'.format(stats['total_strikes']))
    print('   • Tokens: {}'.format(stats['total_tokens']))

    # Get available underlyings
    underlyings = authoritative_option_chain_service.get_available_underlyings()
    print('\n🔍 Available underlyings: {}'.format(underlyings))

    # Get subscription manager
    sub_mgr = get_subscription_manager()
    subscribed_count = 0
    failed_count = 0

    # Subscribe each option chain
    for underlying in underlyings:
        expiries = authoritative_option_chain_service.get_available_expiries(underlying)
        print('\n📈 Processing {}: {} expiries'.format(underlying, len(expiries)))
        
        for expiry in expiries:
            print('   📅 {}'.format(expiry))
            
            # Get option chain from cache
            option_chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying, expiry)
            if not option_chain:
                print('     ❌ No option chain data')
                failed_count += 1
                continue
            
            # Subscribe all strikes
            strikes = option_chain.get('strikes', {})
            for strike_price, strike_data in strikes.items():
                # Subscribe CE
                ce_token = strike_data.get('CE', {}).get('token')
                if ce_token:
                    success, message, ws_id = sub_mgr.subscribe(
                        token=ce_token,
                        symbol=underlying,
                        expiry=expiry,
                        strike=float(strike_price),
                        option_type='CE',
                        tier='TIER_B'
                    )
                    if success:
                        subscribed_count += 1
                    else:
                        failed_count += 1
                
                # Subscribe PE
                pe_token = strike_data.get('PE', {}).get('token')
                if pe_token:
                    success, message, ws_id = sub_mgr.subscribe(
                        token=pe_token,
                        symbol=underlying,
                        expiry=expiry,
                        strike=float(strike_price),
                        option_type='PE',
                        tier='TIER_B'
                    )
                    if success:
                        subscribed_count += 1
                    else:
                        failed_count += 1

    # Final stats
    print('\n📊 Subscription Results:')
    print('   • Subscribed: {}'.format(subscribed_count))
    print('   • Failed: {}'.format(failed_count))

    # Check subscription manager stats
    stats_after = sub_mgr.get_ws_stats()
    print('\n📊 Subscription Manager Stats:')
    print('   • Total subscriptions: {}'.format(stats_after['total_subscriptions']))
    print('   • Tier B: {}'.format(stats_after['tier_b_count']))
    print('   • Tier A: {}'.format(stats_after['tier_a_count']))
    
    print('\n🎯 Next Steps:')
    print('   1. Restart WebSocket feed to include new subscriptions')
    print('   2. Check live data: Watch for [PRICE] messages')
    print('   3. Check ATM strikes: curl http://localhost:8000/api/v2/options/atm/NIFTY')
    print('=' * 60)

if __name__ == "__main__":
    main()
