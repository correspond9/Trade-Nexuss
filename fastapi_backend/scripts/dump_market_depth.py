from app.market.market_state import state
import json

print(json.dumps(list((state.get('depth') or {}).keys()), indent=2))
print('\nFull depth snapshot (truncated):')
for k, v in (state.get('depth') or {}).items():
    print(k, '->', { 'bids': v.get('bids')[:1] if v.get('bids') else [], 'asks': v.get('asks')[:1] if v.get('asks') else [] })
