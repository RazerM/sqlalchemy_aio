import asyncio
import threading
from concurrent.futures import CancelledError
from functools import partial

import outcome

from .base import AsyncEngine, ThreadWorker
from .exc import AlreadyQuit

_STOP = object()


class AsyncioThreadWorker(ThreadWorker):
    def __init__(self, loop=None, *, branch_from=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop

        if branch_from is None:
            self._request_queue = asyncio.Queue(1)
            self._response_queue = asyncio.Queue(1)
            self._thread = threading.Thread(target=self.thread_fn, daemon=True)
            self._thread.start()
        else:
            self._request_queue = branch_from._request_queue
            self._response_queue = branch_from._response_queue
            self._thread = branch_from._thread

        self._branched = branch_from is not None
        self._has_quit = False

    def thread_fn(self):
        while True:
            fut = asyncio.run_coroutine_threadsafe(
                self._request_queue.get(), self._loop)
            try:
                request = fut.result()
            except CancelledError:
                continue

            if request is not _STOP:
                response = outcome.capture(request)
                fut = asyncio.run_coroutine_threadsafe(
                    self._response_queue.put(response), self._loop)
                fut.result()
            else:
                fut = asyncio.run_coroutine_threadsafe(
                    self._response_queue.put(None), self._loop)
                fut.result()
                break

    async def run(self, func, args=(), kwargs=None):
        if self._has_quit:
            raise AlreadyQuit

        if kwargs:
            func = partial(func, *args, **kwargs)
        elif args:
            func = partial(func, *args)

        await self._request_queue.put(func)
        resp = await self._response_queue.get()
        return resp.unwrap()

    async def quit(self):
        if self._has_quit:
            raise AlreadyQuit

        self._has_quit = True

        if self._branched:
            return

        await self._request_queue.put(_STOP)
        await self._response_queue.get()


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
