from app.market.instrument_master.loader import MASTER
MASTER.load()
from app.market.instrument_master.registry import REGISTRY

# Check all available symbols
print("Checking registry structure...")
if hasattr(REGISTRY, 'by_symbol'):
    nifty_syms = [s for s in REGISTRY.by_symbol.keys() if 'NIFTY' in s.upper()]
    print(f"Found {len(nifty_syms)} symbols with NIFTY:")
    for sym in sorted(nifty_syms)[:20]:
        records = REGISTRY.by_symbol[sym]
        print(f"  {sym}: {len(records)} records")

# Check master data
print("\n\nChecking master data...")
if hasattr(MASTER, 'df'):
    df = MASTER.df
    print(f"Total records: {len(df)}")
    nifty_df = df[df['SYM'].str.contains('NIFTY', na=False, case=False)]
    print(f"NIFTY records: {len(nifty_df)}")
    if len(nifty_df) > 0:
        print(f"\nSample NIFTY record:")
        rec = nifty_df.iloc[0]
        for col in ['SYM', 'EXCH', 'EXPIRY', 'SM_EXPIRY_DATE', 'EXPIRY_DATE', 'EXCH_ID']:
            if col in rec:
                print(f"  {col}: {rec[col]}")
