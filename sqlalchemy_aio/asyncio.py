import asyncio
import threading
from concurrent.futures import CancelledError
from functools import partial

import outcome

from .base import AlreadyQuit, AsyncEngine, ThreadWorker

_STOP = object()


class AsyncioThreadWorker(ThreadWorker):
    def __init__(self, loop):
        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop
        self._request_queue = asyncio.Queue(1)
        self._response_queue = asyncio.Queue(1)
        thread = threading.Thread(target=self.thread_fn, daemon=True)
        thread.start()
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

    async def run(_self, _func, *args, **kwargs):
        if _self._has_quit:
            raise AlreadyQuit

        if args or kwargs:
            _func = partial(_func, *args, **kwargs)
        await _self._request_queue.put(_func)
        resp = await _self._response_queue.get()
        return resp.unwrap()

    async def quit(self):
        self._has_quit = True
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

    def _make_worker(self):
        return AsyncioThreadWorker(self._loop)
