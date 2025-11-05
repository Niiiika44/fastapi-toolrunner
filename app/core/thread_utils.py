import asyncio
import functools
import time
from contextlib import asynccontextmanager
import logging


logger = logging.getLogger(__name__)


class ThreadPoolMonitor:
    """
    Monitor threads.
    """
    def __init__(self, max_threads: int):
        self.max_threads = max_threads
        self.semaphore = asyncio.Semaphore(max_threads)

    @property
    def active_threads(self) -> int:
        """
        Number of active threads.
        """
        return self.max_threads - self.semaphore._value


thread_monitor = ThreadPoolMonitor(max_threads=5)  # limit number of parallel threads


@asynccontextmanager
async def _thread_slot():
    """
    Context manager to log threads.
    """
    await thread_monitor.semaphore.acquire()
    try:
        logger.debug("[THREAD] +1 active (%s/%s)",
                     thread_monitor.active_threads, thread_monitor.max_threads)
        yield
    finally:
        thread_monitor.semaphore.release()
        logger.debug("[THREAD] -1 active (%s/%s)",
                     thread_monitor.active_threads, thread_monitor.max_threads)


async def run_in_thread(func, *args, **kwargs):
    """
    Add func to thread pool, log and limit num of parallel threads.
    """
    start = time.perf_counter()
    async with _thread_slot():
        try:
            result = await asyncio.to_thread(functools.partial(func, *args, **kwargs))
            duration = (time.perf_counter() - start) * 1000
            logger.debug("[THREAD] %s done in %.2f ms", func.__name__, duration)
            return result
        except Exception as e:
            logger.exception("[THREAD] Error in %s: %s", func.__name__, e)
            raise
