from app.market.instrument_master.loader import MASTER
MASTER.load()
from app.market.instrument_master.registry import REGISTRY

print("Testing registry...")
exp_nifty = REGISTRY.get_expiries_for_underlying('NIFTY')
print(f'get_expiries_for_underlying(NIFTY): {exp_nifty}')

exp_nifty2 = REGISTRY.get_expiries_for_symbol('NIFTY')
print(f'get_expiries_for_symbol(NIFTY): {exp_nifty2}')

# Check if records exist
nifty_records = REGISTRY.get_by_symbol('NIFTY')
print(f'Total NIFTY records: {len(nifty_records) if nifty_records else 0}')

if nifty_records:
    rec = nifty_records[0]
    print(f'\nSample NIFTY record fields:')
    for key in ['SYM', 'EXCH', 'SEGMENT', 'EXPIRY', 'SM_EXPIRY_DATE', 'EXPIRY_DATE']:
        if key in rec:
            print(f'  {key}: {rec[key]}')
