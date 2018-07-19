import trio
import threading
from functools import partial

import outcome
from trio import Cancelled, RunFinishedError

from .base import AlreadyQuit, AsyncEngine, ThreadWorker

_STOP = object()


class TrioThreadWorker(ThreadWorker):
    def __init__(self):
        self._portal = trio.BlockingTrioPortal()
        self._request_queue = trio.Queue(1)
        self._response_queue = trio.Queue(1)
        thread = threading.Thread(target=self.thread_fn, daemon=True)
        thread.start()
        self._has_quit = False

    def thread_fn(self):
        while True:
            try:
                request = self._portal.run(self._request_queue.get)
            except Cancelled:
                continue
            except RunFinishedError:
                break

            if request is not _STOP:
                response = outcome.capture(request)
                self._portal.run(self._response_queue.put, response)
            else:
                self._portal.run(self._response_queue.put, None)
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


class TrioEngine(AsyncEngine):
    """Mostly like :class:`sqlalchemy.engine.Engine` except some of the methods
    are coroutines."""
    def _make_worker(self):
        return TrioThreadWorker()
