import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.services.nse_reports_service import nse_reports_service


class NSEReportsScheduler:
    def __init__(self) -> None:
        self._task = None
        self.timezone = ZoneInfo("Asia/Kolkata")
        self.run_hour = 8
        self.run_minute = 30

    async def start(self):
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self):
        while True:
            now = datetime.now(self.timezone)
            next_run = now.replace(hour=self.run_hour, minute=self.run_minute, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run + timedelta(days=1)
            wait_seconds = (next_run - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            await nse_reports_service.refresh_daily_reports()


_scheduler_instance = None


def get_nse_reports_scheduler() -> NSEReportsScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = NSEReportsScheduler()
    return _scheduler_instance
