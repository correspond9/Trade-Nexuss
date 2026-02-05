from apscheduler.schedulers.background import BackgroundScheduler
from app.rest.mock_exchange import process_pending_orders

_scheduler = None


def get_mock_exchange_scheduler():
    global _scheduler
    if _scheduler:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(process_pending_orders, "interval", seconds=2, id="mock_exchange_pending_orders")
    return _scheduler
