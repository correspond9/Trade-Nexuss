
import asyncio
import logging
from dhanhq.marketfeed import DhanFeed

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

async def verify():
    print("="*50)
    print("DHAN LIVE CONNECTION TESTER")
    print("="*50)
    
    client_id = input("Enter Client ID: ").strip()
    token = input("Enter Access Token: ").strip()
    
    if not client_id or not token:
        print("Error: Client ID and Token are required.")
        return

    print(f"\n[-] Initializing DhanFeed for {client_id}...")
    
    # Define a simple callback
    def on_message(instance, message):
        print(f"\n[SUCCESS] Received message from Dhan: {message}")
        print("[SUCCESS] Connection Verified!")
        # We can't easily stop the loop from here without a flag, 
        # but seeing one message is enough proof.
    
    try:
        # Initialize exactly as the app does
        feed = DhanFeed(client_id, token, instruments=[(1, "1333")], version="v2")
        
        # Override the callback
        # Note: DhanFeed might expect on_connect / on_message separately depending on version
        # But let's try the standard way
        
        print("[-] Connecting to WebSocket...")
        # run_forever is blocking, so we wrap it or just let it run for a bit
        # But DhanFeed.run_forever() starts the loop. 
        
        # Let's just try to authorize and subscribe
        # We'll use a trick: run it and interrupt if successful
        
        feed.run_forever()
        
    except Exception as e:
        print(f"\n[ERROR] Connection Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Windows SelectorEventLoop policy fix if needed, though 3.10+ handles it better
    # if os.name == 'nt':
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(verify())
