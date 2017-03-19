from sqlalchemy.engine.strategies import DefaultEngineStrategy

from .engine import AsyncioEngine

ASYNCIO_STRATEGY = '_asyncio'


class AsyncioEngineStrategy(DefaultEngineStrategy):
    name = ASYNCIO_STRATEGY
    engine_cls = AsyncioEngine


AsyncioEngineStrategy()
