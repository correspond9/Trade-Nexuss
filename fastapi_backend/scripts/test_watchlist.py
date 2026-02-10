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
    # Tier-A and Tier-B sample symbols to test add/remove
    symbols = [
        {'symbol':'RELIANCE','meta':{'expiry':None,'instrument_type':'EQ'}},
        {'symbol':'CRUDEOIL 26FEB2026 6000 CE','meta':{'expiry':'26FEB2026','instrument_type':'OPTION'}}
    ]

    for s in symbols:
        payload = {'user_id':1, 'symbol': s['symbol']}
        payload.update(s['meta'])
        print('add', s['symbol'], post('/watchlist/add', payload))

    for s in symbols:
        payload = {'user_id':1, 'symbol': s['symbol']}
        print('remove', s['symbol'], post('/watchlist/remove', payload))
