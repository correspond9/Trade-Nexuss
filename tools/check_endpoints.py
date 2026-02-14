import requests

BASE = "http://127.0.0.1:8000/api/v2"

def check(path):
    url = BASE + path
    try:
        r = requests.get(url, timeout=5)
        print(url, r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text[:500])
    except Exception as e:
        print('ERR', url, e)

if __name__ == '__main__':
    check('/market/underlying-ltp/BANKNIFTY')
    check('/available/expiries?underlying=BANKNIFTY')
    check('/live?underlying=BANKNIFTY&expiry=2026-02-12')
    check('/atm/BANKNIFTY')
    check('/cache/stats')
