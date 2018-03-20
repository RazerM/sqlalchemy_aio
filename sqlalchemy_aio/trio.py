from ._base import AsyncEngine
from ._worker import ThreadWorker


class TrioEngine(AsyncEngine):
    """Mostly like :class:`sqlalchemy.engine.Engine` except some of the methods
    are coroutines."""
    def __init__(self, pool, dialect, url, logging_name=None, echo=None,
                 execution_options=None, **kwargs):

        super().__init__(
            pool, dialect, url, logging_name, echo, execution_options, **kwargs)

        self._engine_worker = ThreadWorker()

    async def _run_in_thread(_self, _func, *args, **kwargs):
        return await _self._engine_worker.run(_func, *args, **kwargs)

    def _make_connection_thread_fn(self):
        worker = ThreadWorker()
        return worker.run
