from .exc import AlreadyQuit, BlockingWarning, SQLAlchemyAioDeprecationWarning
from .strategy import ASYNCIO_STRATEGY, TRIO_STRATEGY

__all__ = [
    'ASYNCIO_STRATEGY',
    'TRIO_STRATEGY',
]

__author__ = 'Frazer McLean <frazer@frazermclean.co.uk>'
__version__ = '0.17.0'
__license__ = 'MIT'
__description__ = 'Async support for SQLAlchemy.'
