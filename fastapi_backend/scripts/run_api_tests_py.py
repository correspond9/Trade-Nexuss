import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = 'http://127.0.0.1:8000/api/v2'

def post(path, payload):
    url = BASE + path
    data = json.dumps(payload).encode('utf-8')
    req = Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        resp = urlopen(req, timeout=10)
        return json.load(resp)
    except HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}


def get(path):
    url = BASE + path
    req = Request(url)
    try:
        resp = urlopen(req, timeout=10)
        return json.load(resp)
    except Exception as e:
        return {'error': str(e)}


if __name__ == '__main__':
    # Force markets open
    for ex in ['NSE','BSE','MCX']:
        print('force', ex, post('/admin/market/force', {'exchange': ex, 'state': 'open'}))

    # Update prices
    print('price', post('/admin/price/update', {'symbol':'NIFTY','price':18000}))
    print('price', post('/admin/price/update', {'symbol':'BANKNIFTY','price':43000}))
    print('price', post('/admin/price/update', {'symbol':'SENSEX','price':72000}))
    print('price', post('/admin/price/update', {'symbol':'CRUDEOIL','price':6100}))
    print('price', post('/admin/price/update', {'symbol':'RELIANCE','price':2300}))

    # Seed depths
    depths = {
        'RELIANCE': {'bids':[{'price':2300,'qty':100}], 'asks':[{'price':2301,'qty':100}]},
        'RELIANCE 26FEB2026 3300 CE': {'bids':[{'price':1.0,'qty':100}], 'asks':[{'price':1.5,'qty':100}]},
        'SENSEX 12FEB2026 84000 PE': {'bids':[{'price':10,'qty':50}], 'asks':[{'price':11,'qty':50}]},
        'CRUDEOIL': {'bids':[{'price':6100,'qty':10}], 'asks':[{'price':6105,'qty':10}]},
        'CRUDEOIL 26FEB2026 6000 CE': {'bids':[{'price':5,'qty':20}], 'asks':[{'price':6,'qty':20}]},
    }
    for sym, d in depths.items():
        print('depth', sym, post('/admin/market/depth', {'symbol': sym, 'depth': d}))

    # Add watchlist
    print('watchlist add', post('/watchlist/add', {'user_id':1,'symbol':'NIFTY','expiry':'26FEB2026','instrument_type':'INDEX_OPTION','underlying_ltp':18000}))

    # Place orders
    orders = [
        {'user_id':1,'symbol':'RELIANCE','exchange_segment':'NSE_EQ','transaction_type':'BUY','quantity':1,'order_type':'MARKET','product_type':'MIS'},
        {'user_id':1,'symbol':'RELIANCE 26FEB2026 3300 CE','exchange_segment':'NSE_FNO','transaction_type':'BUY','quantity':1,'order_type':'MARKET','product_type':'MIS'},
        {'user_id':1,'symbol':'SENSEX 12FEB2026 84000 PE','exchange_segment':'BSE_FNO','transaction_type':'BUY','quantity':1,'order_type':'MARKET','product_type':'MIS'},
        {'user_id':1,'symbol':'CRUDEOIL','exchange_segment':'MCX_COMM','transaction_type':'BUY','quantity':1,'order_type':'MARKET','product_type':'MIS'},
        {'user_id':1,'symbol':'CRUDEOIL 26FEB2026 6000 CE','exchange_segment':'MCX_COMM','transaction_type':'BUY','quantity':1,'order_type':'MARKET','product_type':'MIS'},
    ]
    for o in orders:
        print('place', o['symbol'], post('/trading/orders', o))

    print('orders list', get('/trading/orders?user_id=1'))
    print('positions', get('/portfolio/positions'))
