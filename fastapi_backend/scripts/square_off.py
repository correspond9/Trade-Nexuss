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
    pos = get('/portfolio/positions')
    if 'data' not in pos:
        print('positions error', pos)
        raise SystemExit(1)

    for p in pos['data']:
        qty = p.get('qty') or p.get('quantity') or 0
        status = p.get('status')
        if status == 'OPEN' and qty != 0:
            side = 'SELL' if qty > 0 else 'BUY'
            order = {
                'user_id': p.get('user_id', 1),
                'symbol': p['symbol'],
                'exchange_segment': p.get('exchange_segment'),
                'transaction_type': side,
                'quantity': abs(qty),
                'order_type': 'MARKET',
                'product_type': p.get('product_type', 'MIS')
            }
            print('square-off', p['symbol'], order)
            print('result', post('/trading/orders', order))
