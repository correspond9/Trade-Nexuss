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

if __name__ == '__main__':
    # Try allowed index option symbols
    payload = {'user_id':1, 'symbol':'BANKNIFTY', 'expiry':'26FEB2026', 'instrument_type':'INDEX_OPTION', 'underlying_ltp':43000}
    print('add BANKNIFTY', post('/watchlist/add', payload))
    print('remove BANKNIFTY', post('/watchlist/remove', {'user_id':1, 'symbol':'BANKNIFTY','expiry':'26FEB2026'}))
