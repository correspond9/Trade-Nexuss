from app.market.instrument_master.registry import REGISTRY


def show(symbol):
    print(f"\n=== {symbol} ===")
    if not REGISTRY.loaded:
        REGISTRY.load()

    by_sym = REGISTRY.get_by_symbol(symbol)
    print(f"Records for symbol: {len(by_sym)}")
    for r in by_sym[:5]:
        print({'SECURITY_ID': r.get('SECURITY_ID'), 'SYMBOL_NAME': r.get('SYMBOL_NAME'), 'SM_EXPIRY_DATE': r.get('SM_EXPIRY_DATE'), 'EXCH_ID': r.get('EXCH_ID'), 'INSTRUMENT_TYPE': r.get('INSTRUMENT_TYPE'), 'LOT_SIZE': r.get('LOT_SIZE')})

    exps = REGISTRY.get_expiries_for_underlying(symbol)
    print(f"Expiries for underlying: {exps[:5]}")

    # Show nearest MCX future if applicable
    try:
        mcx = REGISTRY.get_nearest_mcx_future(symbol)
        if mcx:
            print('MCX nearest future:', mcx)
    except Exception as e:
        print('MCX lookup error:', e)


if __name__ == '__main__':
    targets = ['RELIANCE', 'SENSEX', 'CRUDEOIL', 'NIFTY', 'BANKNIFTY']
    for t in targets:
        show(t)
