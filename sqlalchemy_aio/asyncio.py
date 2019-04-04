import asyncio
import threading
from concurrent.futures import CancelledError
from functools import partial
from queue import Queue, Empty

from .base import AsyncEngine, ThreadWorker
from .exc import AlreadyQuit

_STOP = object()


class AsyncioThreadWorker(ThreadWorker):
    def __init__(self, loop=None, *, branch_from=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop

        if branch_from is None:
            self._queue = Queue()
            self._thread = threading.Thread(target=self.thread_fn, daemon=True, name="AlchemyAsyncWorker")
            self._thread.start()
        else:
            self._queue = branch_from._queue
            self._thread = branch_from._thread

        self._branched = branch_from is not None
        self._has_quit = False

    def thread_fn(self):
        while True:
            try:
                future, func = self._queue.get(timeout=0.1)
            except Empty:
                continue
            if func is not None:
                try:
                    result = func()
                    self._loop.call_soon_threadsafe(future.set_result, result)
                except Exception as e:
                    self._loop.call_soon_threadsafe(future.set_exception, e)
            else:
                self._loop.call_soon_threadsafe(future.set_result, None)
                break

    async def run(self, func, args=(), kwargs=None):
        if self._has_quit:
            raise AlreadyQuit

        if kwargs:
            func = partial(func, *args, **kwargs)
        elif args:
            func = partial(func, *args)

        future = self._loop.create_future()
        self._queue.put_nowait((future, func))
        return await future

    async def quit(self):
        if self._has_quit:
            raise AlreadyQuit

        self._has_quit = True

        if self._branched:
            return
        future = self._loop.create_future()
        self._queue.put_nowait((future, None))
        await future

        # await self._request_queue.put(_STOP)
        # await self._response_queue.get()


class AsyncioEngine(AsyncEngine):
    """Mostly like :class:`sqlalchemy.engine.Engine` except some of the methods
    are coroutines."""
    def __init__(self, pool, dialect, url, logging_name=None, echo=None,
                 execution_options=None, loop=None, **kwargs):

        super().__init__(
            pool, dialect, url, logging_name, echo, execution_options, **kwargs)

        self._loop = loop

    def _make_worker(self, *, branch_from=None):
        return AsyncioThreadWorker(self._loop, branch_from=branch_from)
