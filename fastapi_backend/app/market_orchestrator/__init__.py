"""Market data orchestrator package."""

from app.market_orchestrator.orchestrator_core import MarketDataOrchestrator

ORCHESTRATOR = MarketDataOrchestrator()

def get_orchestrator() -> MarketDataOrchestrator:
    return ORCHESTRATOR
