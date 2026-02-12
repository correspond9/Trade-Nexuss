from app.market_orchestrator import get_orchestrator

print('Triggering start_streams_sync()')
get_orchestrator().start_streams_sync()
print('Triggered')
