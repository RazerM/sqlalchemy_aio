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

    def _run_in_thread(self, func, *args, **kwargs):
        if kwargs:
            func = partial(func, **kwargs)

        return self._loop.run_in_executor(self._executor, func, *args)

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

    async def execute(self, *args, **kwargs):
        rp = await self._run_in_thread(self._engine.execute, *args, **kwargs)
        return AsyncioResultProxy(rp, self)

    async def has_table(self, table_name, schema=None):
        return await self._run_in_thread(self._engine.has_table, table_name, schema)

    async def table_names(self, schema=None, connection=None):
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

    def begin(self, *args, **kwargs):
        return _TransactionContextManager(self._begin(*args, **kwargs))

    async def _begin(self, *args, **kwargs):
        transaction = await self._engine._run_in_thread(
            self._connection.begin, *args, **kwargs)
        return AsyncioTransaction(transaction, self._engine)


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
