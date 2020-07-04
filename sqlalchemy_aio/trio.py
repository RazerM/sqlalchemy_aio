import threading
from contextlib import suppress
from functools import partial

import outcome
import trio
from trio import Cancelled, RunFinishedError

from .base import AsyncEngine, ThreadWorker
from .exc import AlreadyQuit

_STOP = object()


class TrioThreadWorker(ThreadWorker):
    def __init__(self, *, branch_from=None):
        if branch_from is None:
            self._trio_token = trio.lowlevel.current_trio_token()
            send_to_thread, receive_from_trio = trio.open_memory_channel(1)
            send_to_trio, receive_from_thread = trio.open_memory_channel(1)

            self._send_to_thread = send_to_thread
            self._send_to_trio = send_to_trio
            self._receive_from_trio = receive_from_trio
            self._receive_from_thread = receive_from_thread

            self._thread = threading.Thread(target=self.thread_fn, daemon=True)
            self._thread.start()
        else:
            self._send_to_thread = branch_from._send_to_thread
            self._send_to_trio = branch_from._send_to_trio
            self._receive_from_trio = branch_from._receive_from_trio
            self._receive_from_thread = branch_from._receive_from_thread
            self._thread = branch_from._thread

        self._branched = branch_from is not None
        self._has_quit = False

    def thread_fn(self):
        while True:
            try:
                request = trio.from_thread.run(
                    self._receive_from_trio.receive, trio_token=self._trio_token
                )
            except (Cancelled, RunFinishedError):
                break
            except trio.EndOfChannel:
                with suppress(Cancelled, RunFinishedError):
                    trio.from_thread.run(
                        self._send_to_trio.aclose, trio_token=self._trio_token
                    )
                break

            response = outcome.capture(request)
            trio.from_thread.run(
                self._send_to_trio.send, response, trio_token=self._trio_token
            )

    async def run(self, func, args=(), kwargs=None):
        if self._has_quit:
            raise AlreadyQuit

        if kwargs:
            func = partial(func, *args, **kwargs)
        elif args:
            func = partial(func, *args)

        await self._send_to_thread.send(func)
        resp = await self._receive_from_thread.receive()
        return resp.unwrap()

    async def quit(self):
        if self._has_quit:
            raise AlreadyQuit

        self._has_quit = True

        if self._branched:
            return

        await self._send_to_thread.aclose()


class TrioEngine(AsyncEngine):
    """Mostly like :class:`sqlalchemy.engine.Engine` except some of the methods
    are coroutines."""
    def _make_worker(self, *, branch_from=None):
        return TrioThreadWorker(branch_from=branch_from)
