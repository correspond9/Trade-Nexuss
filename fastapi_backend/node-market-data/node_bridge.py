import requests
import threading
import time
from app.market.live_prices import update_price

NODE_URL = "http://127.0.0.1:9100/prices"

def start_node_bridge():
    def loop():
        while True:
            try:
                r = requests.get(NODE_URL, timeout=1).json()
                if "NIFTY" in r:
                    update_price("NIFTY", float(r["NIFTY"]))
                if "SENSEX" in r:
                    update_price("SENSEX", float(r["SENSEX"]))
                if "CRUDEOIL" in r:
                    update_price("CRUDEOIL", float(r["CRUDEOIL"]))
            except:
                pass
            time.sleep(0.5)
    threading.Thread(target=loop, daemon=True).start()
