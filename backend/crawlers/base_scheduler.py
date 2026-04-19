"""
Base scheduler with retry, error logging, and alert logic
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from backend.ai_db.models import CrawlErrorLog

logger = logging.getLogger(__name__)


class BaseScheduler(ABC):
    """Abstract base class for crawler schedulers"""

    def __init__(self, name: str, max_retries: int = 3, alert_threshold: int = 5):
        self.name = name
        self.max_retries = max_retries
        self.alert_threshold = alert_threshold
        self.consecutive_failures = 0

    @abstractmethod
    async def crawl(self) -> None:
        """Execute crawl logic - subclasses implement"""
        pass

    async def run(self) -> None:
        """Scheduler run entry point with retry logic"""
        for attempt in range(self.max_retries):
            try:
                await self.crawl()
                self.consecutive_failures = 0
                logger.info(f"{self.name}: crawl successful")
                return
            except Exception as e:
                logger.warning(f"{self.name}: attempt {attempt + 1} failed: {e}")
                await self._log_error(str(e))
                if attempt == self.max_retries - 1:
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= self.alert_threshold:
                        await self._send_alert()

    async def _log_error(self, error_msg: str) -> None:
        """Log error to database"""
        await CrawlErrorLog.create(
            crawler_name=self.name,
            error_type="crawl_failure",
            error_message=error_msg[:1000],
            retry_count=self.max_retries
        )

    async def _send_alert(self) -> None:
        """Send alert when consecutive failures exceed threshold"""
        logger.error(f"ALERT: {self.name} failed {self.consecutive_failures} times consecutively")
