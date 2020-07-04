import asyncio
import threading
import warnings
from concurrent.futures import CancelledError
from functools import partial

import outcome

from .base import AsyncEngine, ThreadWorker
from .exc import AlreadyQuit, SQLAlchemyAioDeprecationWarning


class Request:
    def __init__(self, func):
        self.func = func
        self.finished = asyncio.Event()
        self.response = None

    def set_finished(self):
        """Needed to be executed in the same thread as the loop.
        Since Event() is not thread-safe.
        """
        self.finished.set()


class AsyncioThreadWorker(ThreadWorker):
    def __init__(self, loop=None, *, branch_from=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop

        if branch_from is None:
            self._request_queue = asyncio.Queue(1, loop=loop)
            self._thread = threading.Thread(target=self.thread_fn, daemon=True)
            self._thread.start()
        else:
            self._request_queue = branch_from._request_queue
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

            if request.func is not None:
                request.response = outcome.capture(request.func)

                self._loop.call_soon_threadsafe(request.set_finished)
            else:
                self._loop.call_soon_threadsafe(request.set_finished)
                break

    async def run(self, func, args=(), kwargs=None):
        if self._has_quit:
            raise AlreadyQuit

        if kwargs:
            func = partial(func, *args, **kwargs)
        elif args:
            func = partial(func, *args)

        request = Request(func)
        await self._request_queue.put(request)
        await request.finished.wait()
        return request.response.unwrap()

    async def quit(self):
        if self._has_quit:
            raise AlreadyQuit

        self._has_quit = True

        if self._branched:
            return

        stop = Request(None)
        await self._request_queue.put(stop)
        await stop.finished.wait()


class AsyncioEngine(AsyncEngine):
    """Mostly like :class:`sqlalchemy.engine.Engine` except some of the methods
    are coroutines."""
    def __init__(self, pool, dialect, url, logging_name=None, echo=None,
                 execution_options=None, loop=None, **kwargs):

        super().__init__(
            pool, dialect, url, logging_name, echo, execution_options, **kwargs)

        if loop is not None:
            warnings.warn(
                'The loop argument is deprecated.',
                category=SQLAlchemyAioDeprecationWarning,
                stacklevel=4,
            )

        self._loop = loop

    def _make_worker(self, *, branch_from=None):
        return AsyncioThreadWorker(self._loop, branch_from=branch_from)
