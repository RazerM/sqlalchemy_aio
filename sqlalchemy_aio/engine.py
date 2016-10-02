import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from represent import ReprHelper
from sqlalchemy import util
from sqlalchemy.engine import Engine


class AsyncioEngine:
    def __init__(self, pool, dialect, url, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()

        self._engine = Engine(pool, dialect, url, **kwargs)
        self._loop = loop
        if executor is None:
            # Need max_workers=1 for sqlite
            executor = ThreadPoolExecutor(max_workers=1)
        self._executor = executor

    def _run_in_thread(_engine_self, _engine_func, *args, **kwargs):
        # use _engine_self and _engine_func in case we're called with kwargs
        # "self" or "func".
        if kwargs:
            _engine_func = partial(_engine_func, **kwargs)

        return _engine_self._loop.run_in_executor(
            _engine_self._executor, _engine_func, *args)

    @property
    def dialect(self):
        return self._engine.dialect

    @property
    def _has_events(self):
        return self._engine._has_events

    @property
    def _execution_options(self):
        return self._engine._execution_options

    def _should_log_info(self):
        return self._engine._should_log_info()

    def connect(self):
        return _ConnectionContextManager(self._connect())

    async def _connect(self):
        connection = await self._run_in_thread(self._engine.connect)
        return AsyncioConnection(connection, self)

    def begin(self, close_with_result=False):
        return _EngineTransactionContextManager(self, close_with_result)

    async def execute(self, *args, **kwargs):
        rp = await self._run_in_thread(self._engine.execute, *args, **kwargs)
        return AsyncioResultProxy(rp, self)

    async def has_table(self, table_name, schema=None):
        return await self._run_in_thread(self._engine.has_table, table_name, schema)

    async def table_names(self, schema=None, connection=None):
        if connection is not None:
            connection = connection._connection

        return await self._run_in_thread(
            self._engine.table_names, schema, connection)

    def __repr__(self):
        r = ReprHelper(self)
        r.parantheses = ('<', '>')
        r.positional_from_attr('_engine')
        return str(r)


class AsyncioConnection:
    def __init__(self, connection, engine: AsyncioEngine):
        self._connection = connection
        self._engine = engine

    async def execute(self, *args, **kwargs):
        rp = await self._engine._run_in_thread(
            self._connection.execute, *args, **kwargs)
        return AsyncioResultProxy(rp, self._engine)

    def close(self, *args, **kwargs):
        return self._engine._run_in_thread(
            self._connection.close, *args, **kwargs)

    @property
    def closed(self):
        return self._connection.closed

    def begin(self):
        return _TransactionContextManager(self._begin())

    async def _begin(self):
        transaction = await self._engine._run_in_thread(
            self._connection.begin)
        return AsyncioTransaction(transaction, self._engine)

    def begin_nested(self):
        return _TransactionContextManager(self._begin_nested())

    async def _begin_nested(self):
        transaction = await self._engine._run_in_thread(
            self._connection.begin_nested)
        return AsyncioTransaction(transaction, self._engine)

    def in_transaction(self):
        return self._connection.in_transaction()


class AsyncioTransaction:
    def __init__(self, transaction, engine):
        self._transaction = transaction
        self._engine = engine

    async def commit(self):
        return await self._engine._run_in_thread(self._transaction.commit)

    async def rollback(self):
        return await self._engine._run_in_thread(self._transaction.rollback)

    async def close(self):
        return await self._engine._run_in_thread(self._transaction.close)


class AsyncioResultProxy:
    def __init__(self, result_proxy, engine: AsyncioEngine):
        self._result_proxy = result_proxy
        self._engine = engine

    async def fetchone(self):
        return await self._engine._run_in_thread(self._result_proxy.fetchone)

    async def fetchall(self):
        return await self._engine._run_in_thread(self._result_proxy.fetchall)

    async def scalar(self):
        return await self._engine._run_in_thread(self._result_proxy.scalar)

    async def first(self):
        return await self._engine._run_in_thread(self._result_proxy.first)

    async def keys(self):
        return await self._engine._run_in_thread(self._result_proxy.keys)

    async def close(self):
        return await self._engine._run_in_thread(self._result_proxy.close)

    @property
    def returns_rows(self):
        return self._result_proxy.returns_rows

    @property
    def rowcount(self):
        return self._result_proxy.rowcount

    @property
    def inserted_primary_key(self):
        return self._result_proxy.inserted_primary_key


class _BaseContextManager(Coroutine):
    """Allow ``async with <coroutine>`` or ``await <coroutine>``."""
    __slots__ = ('_coro', '_result')

    def __init__(self, coro):
        self._coro = coro
        self._result = None

    def send(self, value):
        return self._coro.send(value)

    def throw(self, typ, val=None, tb=None):
        if val is None:
            return self._coro.throw(typ)
        elif tb is None:
            return self._coro.throw(typ, val)
        else:
            return self._coro.throw(typ, val, tb)

    def close(self):
        return self._coro.close()

    def __await__(self):
        return self._coro.__await__()

    async def __aenter__(self):
        self._result = await self._coro
        return self._result


class _EngineTransactionContextManager:
    __slots__ = ('_engine', '_close_with_result', '_context')

    def __init__(self, engine: AsyncioEngine, close_with_result):
        self._engine = engine
        self._close_with_result = close_with_result

    async def __aenter__(self):
        self._context = await self._engine._run_in_thread(
            self._engine._engine.begin, self._close_with_result)

        return AsyncioConnection(self._context.__enter__(), self._engine)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._engine._run_in_thread(
            self._context.__exit__, exc_type, exc_val, exc_tb)


class _ConnectionContextManager(_BaseContextManager):
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._result.close()


class _TransactionContextManager(_BaseContextManager):
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and self._result._transaction.is_active:
            try:
                await self._result.commit()
            except:
                with util.safe_reraise():
                    await self._result.rollback()
        else:
            await self._result.rollback()
