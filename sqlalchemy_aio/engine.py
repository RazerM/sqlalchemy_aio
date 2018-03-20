import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from ._base import AsyncEngine, _TransactionContextManager


async def _run_in_executor(_executor, _func, _loop=None, *args, **kwargs):
    # use _executor and _func in case we're called with kwargs
    # "executor" or "func".
    if kwargs:
        _func = partial(_func, **kwargs)

    if _loop is None:
        _loop = asyncio.get_event_loop()

    return await _loop.run_in_executor(_executor, _func, *args)


class AsyncioEngine(AsyncEngine):
    """Mostly like :class:`sqlalchemy.engine.Engine` except some of the methods
    are coroutines."""
    def __init__(self, pool, dialect, url, logging_name=None, echo=None,
                 execution_options=None, loop=None, **kwargs):

        super().__init__(
            pool, dialect, url, logging_name, echo, execution_options, **kwargs)

        self._loop = loop

        max_workers = None

        # https://www.python.org/dev/peps/pep-0249/#threadsafety
        if dialect.dbapi.threadsafety < 2:
            # This might seem overly-restrictive, but when we instantiate an
            # AsyncioResultProxy from AsyncioEngine.execute, subsequent
            # fetchone calls could be in different threads. Let's limit to one.
            max_workers = 1

        self._engine_executor = ThreadPoolExecutor(max_workers=max_workers)

    async def _run_in_thread(_self, _func, *args, **kwargs):
        return await _run_in_executor(
            _self._engine_executor, _func, _self._loop, *args, **kwargs)

    def _make_connection_thread_fn(self):
        executor = ThreadPoolExecutor(max_workers=1)

        async def thread_fn(_func, *args, **kwargs):
            return await _run_in_executor(
                executor, _func, self._loop, *args, **kwargs)

        return thread_fn
