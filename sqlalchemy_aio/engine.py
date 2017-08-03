import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from represent import ReprHelper
from sqlalchemy import util
from sqlalchemy.engine import Engine


async def _run_in_executor(_executor, _func, _loop=None, *args, **kwargs):
    # use _executor and _func in case we're called with kwargs
    # "executor" or "func".
    if kwargs:
        _func = partial(_func, **kwargs)

    if _loop is None:
        _loop = asyncio.get_event_loop()

    return await _loop.run_in_executor(_executor, _func, *args)


class AsyncioEngine:
    """Mostly like :class:`sqlalchemy.engine.Engine` except some of the methods
    are coroutines."""
    def __init__(self, pool, dialect, url, logging_name=None, echo=None,
                 execution_options=None, loop=None, **kwargs):

        self._engine = Engine(
            pool, dialect, url, logging_name=logging_name, echo=echo,
            execution_options=execution_options, **kwargs)

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

    @property
    def dialect(self):
        return self._engine.dialect

    @property
    def _has_events(self):
        return self._engine._has_events

    @property
    def logger(self):
        return self._engine.logger

    @property
    def _execution_options(self):
        return self._engine._execution_options

    def _should_log_info(self):
        return self._engine._should_log_info()

    def connect(self):
        """Like :meth:`Engine.connect <sqlalchemy.engine.Engine.connect>`, but
        returns an awaitable that can also be used as an asynchronous context
        manager.

        Examples:
            .. code-block:: python

                conn = await engine.connect()
                await conn.execute(...)
                await conn.close()

            .. code-block:: python

                async with engine.connect() as conn:
                    await conn.execute(...)
        """
        return _ConnectionContextManager(self._connect())

    async def _connect(self):
        executor = ThreadPoolExecutor(max_workers=1)

        connection = await _run_in_executor(
            executor, self._engine.connect, self._loop)
        return AsyncioConnection(connection, executor, self._loop)

    def begin(self, close_with_result=False):
        """Like :meth:`Engine.begin <sqlalchemy.engine.Engine.begin>`, but
        returns an asynchronous context manager.

        Example:
            .. code-block:: python

                async with engine.begin():
                    await engine.execute(...)
        """
        return _EngineTransactionContextManager(self, close_with_result)

    async def execute(self, *args, **kwargs):
        """Like :meth:`Engine.execute <sqlalchemy.engine.Engine.execute>`, but
        is a coroutine that returns an :class:`AsyncioResultProxy`.

        Example:
            .. code-block:: python

                result = await engine.execute(...)
                data = await result.fetchall()

        .. warning::

            Make sure to explicitly call :meth:`AsyncioResultProxy.close` if the
            :class:`~sqlalchemy.engine.ResultProxy` has pending rows remaining
            otherwise it will be closed during garbage collection. With SQLite,
            this will raise an exception since the DBAPI connection was created
            in a different thread.
        """
        rp = await self._run_in_thread(self._engine.execute, *args, **kwargs)
        return AsyncioResultProxy(rp, self._run_in_thread)

    async def scalar(self, *args, **kwargs):
        """Like :meth:`Connection.scalar <sqlalchemy.engine.Engine.scalar>`,
        but is a coroutine.
        """
        rp = await self.execute(*args, **kwargs)
        return await rp.scalar()

    async def has_table(self, table_name, schema=None):
        """Like :meth:`Engine.has_table <sqlalchemy.engine.Engine.has_table>`,
        but is a coroutine.
        """
        return await self._run_in_thread(
            self._engine.has_table, table_name, schema)

    async def table_names(
            self, schema=None, connection: 'AsyncioConnection' = None):
        """Like :meth:`Engine.table_names <sqlalchemy.engine.Engine.table_names>`,
        but is a coroutine.
        """
        run_in_thread = self._run_in_thread

        if connection is not None:
            run_in_thread = connection._run_in_thread
            connection = connection._connection

        return await run_in_thread(self._engine.table_names, schema, connection)

    def __repr__(self):
        r = ReprHelper(self)
        r.parantheses = ('<', '>')
        r.positional_from_attr('_engine')
        return str(r)


class AsyncioConnection:
    """Mostly like :class:`sqlalchemy.engine.Connection` except some of the
    methods are coroutines.
    """
    def __init__(self, connection, executor, loop=None):
        self._connection = connection
        self._executor = executor
        self._loop = loop

    async def _run_in_thread(_self, _func, *args, **kwargs):
        return await _run_in_executor(
            _self._executor, _func, _self._loop, *args, **kwargs)

    async def execute(self, *args, **kwargs):
        """Like :meth:`Connection.execute <sqlalchemy.engine.Connection.execute>`,
        but is a coroutine that returns an :class:`AsyncioResultProxy`.

        Example:
            .. code-block:: python

                result = await conn.execute(...)
                data = await result.fetchall()

        .. warning::

            Make sure to explicitly call :meth:`AsyncioResultProxy.close` if the
            :class:`~sqlalchemy.engine.ResultProxy` has pending rows remaining
            otherwise it will be closed during garbage collection. With SQLite,
            this will raise an exception since the DBAPI connection was created
            in a different thread.
        """
        rp = await self._run_in_thread(self._connection.execute, *args, **kwargs)
        return AsyncioResultProxy(rp, self._run_in_thread)

    async def scalar(self, *args, **kwargs):
        """Like :meth:`Connection.scalar <sqlalchemy.engine.Connection.scalar>`,
        but is a coroutine.
        """
        rp = await self.execute(*args, **kwargs)
        return await rp.scalar()

    async def close(self, *args, **kwargs):
        """Like :meth:`Connection.close <sqlalchemy.engine.Connection.close>`,
        but is a coroutine.
        """
        return await self._run_in_thread(self._connection.close, *args, **kwargs)

    @property
    def closed(self):
        """Like the :attr:`Connection.closed\
        <sqlalchemy.engine.Connection.closed>` attribute.
        """
        return self._connection.closed

    def begin(self):
        """Like :meth:`Connection.begin <sqlalchemy.engine.Connection.begin>`,
        but returns an awaitable that can also be used as an asynchronous
        context manager.

        Examples:
            .. code-block:: python

                async with conn.begin() as trans:
                    await conn.execute(...)
                    await conn.execute(...)

            .. code-block:: python

                trans = await conn.begin():
                await conn.execute(...)
                await conn.execute(...)
                await trans.commit()
        """
        return _TransactionContextManager(self._begin())

    async def _begin(self):
        transaction = await self._run_in_thread(self._connection.begin)
        return AsyncioTransaction(transaction, self._run_in_thread)

    def begin_nested(self):
        """Like :meth:`Connection.begin_nested\
        <sqlalchemy.engine.Connection.begin_nested>`, but returns an awaitable
        that can also be used as an asynchronous context manager.

        .. seealso:: :meth:`begin` for examples.
        """
        return _TransactionContextManager(self._begin_nested())

    async def _begin_nested(self):
        transaction = await self._run_in_thread(self._connection.begin_nested)
        return AsyncioTransaction(transaction, self._run_in_thread)

    def in_transaction(self):
        """Like the :attr:`Connection.in_transaction\
        <sqlalchemy.engine.Connection.in_transaction>` attribute.
        """
        return self._connection.in_transaction()


class AsyncioTransaction:
    """Mostly like :class:`sqlalchemy.engine.Transaction` except some of the
    methods are coroutines.
    """
    def __init__(self, transaction, run_in_thread):
        self._transaction = transaction
        self._run_in_thread = run_in_thread

    async def commit(self):
        """Like :meth:`Transaction.commit <sqlalchemy.engine.Transaction.commit>`,
        but is a coroutine.
        """
        return await self._run_in_thread(self._transaction.commit)

    async def rollback(self):
        """Like :meth:`Transaction.rollback <sqlalchemy.engine.Transaction.rollback>`,
        but is a coroutine.
        """
        return await self._run_in_thread(self._transaction.rollback)

    async def close(self):
        """Like :meth:`Transaction.close <sqlalchemy.engine.Transaction.close>`,
        but is a coroutine.
        """
        return await self._run_in_thread(self._transaction.close)


class _AsyncioResultProxyIterator:
    def __init__(self, result_proxy, run_in_thread):
        self._result_proxy = result_proxy
        self._run_in_thread = run_in_thread

    def __aiter__(self):
        return self

    async def __anext__(self):
        row = await self._run_in_thread(self._result_proxy.fetchone)
        if row is None:
            raise StopAsyncIteration()
        else:
            return row


class AsyncioResultProxy:
    """Mostly like :class:`sqlalchemy.engine.ResultProxy` except some of the
    methods are coroutines.
    """
    def __init__(self, result_proxy, run_in_thread):
        self._result_proxy = result_proxy
        self._run_in_thread = run_in_thread

    def __aiter__(self):
        return _AsyncioResultProxyIterator(
            self._result_proxy,
            self._run_in_thread)

    async def fetchone(self):
        """Like :meth:`ResultProxy.fetchone\
        <sqlalchemy.engine.ResultProxy.fetchone>`, but is a coroutine.
        """
        return await self._run_in_thread(self._result_proxy.fetchone)

    async def fetchmany(self, size=None):
        """Like :meth:`ResultProxy.fetchmany\
        <sqlalchemy.engine.ResultProxy.fetchmany>`, but is a coroutine.
        """
        return await self._run_in_thread(self._result_proxy.fetchmany, size=size)

    async def fetchall(self):
        """Like :meth:`ResultProxy.fetchall\
        <sqlalchemy.engine.ResultProxy.fetchall>`, but is a coroutine.
        """
        return await self._run_in_thread(self._result_proxy.fetchall)

    async def scalar(self):
        """Like :meth:`ResultProxy.scalar\
        <sqlalchemy.engine.ResultProxy.scalar>`, but is a coroutine.
        """
        return await self._run_in_thread(self._result_proxy.scalar)

    async def first(self):
        """Like :meth:`ResultProxy.first\
        <sqlalchemy.engine.ResultProxy.first>`, but is a coroutine.
        """
        return await self._run_in_thread(self._result_proxy.first)

    async def keys(self):
        """Like :meth:`ResultProxy.keys\
        <sqlalchemy.engine.ResultProxy.keys>`, but is a coroutine.
        """
        return await self._run_in_thread(self._result_proxy.keys)

    async def close(self):
        """Like :meth:`ResultProxy.close\
        <sqlalchemy.engine.ResultProxy.close>`, but is a coroutine.
        """
        return await self._run_in_thread(self._result_proxy.close)

    @property
    def returns_rows(self):
        """Like the :attr:`ResultProxy.returns_rows\
        <sqlalchemy.engine.ResultProxy.returns_rows>` attribute.
        """
        return self._result_proxy.returns_rows

    @property
    def rowcount(self):
        """Like the :attr:`ResultProxy.rowcount\
        <sqlalchemy.engine.ResultProxy.rowcount>` attribute.
        """
        return self._result_proxy.rowcount

    @property
    def inserted_primary_key(self):
        """Like the :attr:`ResultProxy.inserted_primary_key\
        <sqlalchemy.engine.ResultProxy.inserted_primary_key>` attribute.
        """
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

        return AsyncioConnection(
            self._context.__enter__(), self._engine._engine_executor,
            self._engine._loop)

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
