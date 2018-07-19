from sqlalchemy.engine.strategies import DefaultEngineStrategy

from .asyncio import AsyncioEngine
try:
    from .trio import TrioEngine
except ImportError:
    TrioEngine = None

ASYNCIO_STRATEGY = '_asyncio'
TRIO_STRATEGY = '_trio'


class AsyncioEngineStrategy(DefaultEngineStrategy):
    name = ASYNCIO_STRATEGY
    engine_cls = AsyncioEngine


AsyncioEngineStrategy()


if TrioEngine is not None:
    class TrioEngineStrategy(DefaultEngineStrategy):
        name = TRIO_STRATEGY
        engine_cls = TrioEngine

    TrioEngineStrategy()
