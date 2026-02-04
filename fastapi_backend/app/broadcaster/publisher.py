
# Broadcasts market data to frontend WS clients
clients = []

async def publish(data):
    for ws in clients:
        await ws.send_json(data)
