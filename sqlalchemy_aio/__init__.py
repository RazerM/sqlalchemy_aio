from .strategy import ASYNCIO_STRATEGY, AsyncioEngineStrategy

__all__ = [
    'ASYNCIO_STRATEGY',
]

__author__ = 'Frazer McLean <frazer@frazermclean.co.uk>'
__version__ = '0.10.0'
__license__ = 'MIT'
__description__ = 'Asyncio strategy for SQLAlchemy.'

AsyncioEngineStrategy()
