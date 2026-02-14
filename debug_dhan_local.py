
import sys
import os
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_dhan_connection():
    print("[-] Testing DhanHQ Library Import...")
    try:
        import dhanhq
        from dhanhq.marketfeed import DhanFeed
        print(f"[+] DhanHQ imported successfully.")
    except ImportError as e:
        print(f"[!] Failed to import dhanhq: {e}")
        return

    print("[-] Checking dependencies...")
    try:
        import pandas
        import OpenSSL
        import websockets
        print("[+] Dependencies (pandas, pyOpenSSL, websockets) found.")
    except ImportError as e:
        print(f"[!] Missing dependency: {e}")
        return

    print("[-] Checking Lock Port (8765)...")
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 8765))
    if result == 0:
        print("[!] Port 8765 is OPEN (Lock held). This is expected if the backend is running.")
    else:
        print("[+] Port 8765 is CLOSED (Lock free). Backend feed is likely not running.")
    sock.close()

    print("\n[-] Simulation of Feed Class Resolution...")
    # Mimic live_feed.py logic
    try:
        import importlib
        marketfeed = importlib.import_module("dhanhq.marketfeed")
        found = False
        for name in ("DhanFeed", "MarketFeed", "MarketFeedV2", "DhanMarketFeed", "MarketFeedWS"):
            cls = getattr(marketfeed, name, None)
            if cls:
                print(f"[+] Found compatible feed class: {name}")
                found = True
                break
        if not found:
            print("[!] No compatible feed class found in dhanhq.marketfeed")
    except Exception as e:
        print(f"[!] Resolution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_dhan_connection())
