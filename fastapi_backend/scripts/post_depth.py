import json
import sys
from urllib.request import Request, urlopen

def post(symbol, depth):
    url = 'http://127.0.0.1:8000/api/v2/admin/market/depth'
    payload = json.dumps({'symbol': symbol, 'depth': depth}).encode('utf-8')
    req = Request(url, data=payload, headers={'Content-Type': 'application/json'})
    resp = urlopen(req, timeout=10)
    print(resp.read().decode())

if __name__ == '__main__':
    sym = sys.argv[1]
    # simple hardcoded depth sample
    depth = {
        'bids': [{'price': float(sys.argv[2]) if len(sys.argv)>2 else 1.0, 'qty': 100}],
        'asks': [{'price': float(sys.argv[3]) if len(sys.argv)>3 else 1.5, 'qty': 100}],
    }
    post(sym, depth)
