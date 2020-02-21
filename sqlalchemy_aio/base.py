import warnings
import weakref
from abc import ABC, abstractmethod
from collections.abc import Coroutine

from represent import ReprHelper
from sqlalchemy.engine import Engine
from sqlalchemy.exc import StatementError
from sqlalchemy import util
from sqlalchemy.log import Identified

from .exc import AlreadyQuit, BlockingWarning


class AsyncEngine(Identified, ABC):
    def __init__(self, pool, dialect, url, logging_name=None, echo=None,
                 execution_options=None, **kwargs):
        self._engine = Engine(
            pool, dialect, url, logging_name=logging_name, echo=echo,
            execution_options=execution_options, **kwargs)

        self._engine_worker = None

    @abstractmethod
    def _make_worker(self, *, branch_from=None):
        raise NotImplementedError

    async def _run_in_thread(_self, _func, *args, **kwargs):
        """Unlike the public-facing `run_in_thread` method, we want this one
        to let us call SQLAlchemy methods like normal internally.
        """
        if _self._engine_worker is None:
            _self._engine_worker = _self._make_worker()

        return await _self._engine_worker.run(_func, args, kwargs)

    async def run_in_thread(self, func, *args):
        """Run a synchronous function in the engine's worker thread.

        Example:
            The following blocking function:

            .. code-block:: python

                some_fn(engine.sync_engine)

            can be called like this instead:

            .. code-block:: python

                await engine.run_in_thread(some_fn, engine.sync_engine)

        Parameters:
            func: A synchronous function.
            args: Positional arguments to be passed to `func`. If you need to
                pass keyword arguments, then use :func:`functools.partial`.
        """
        if self._engine_worker is None:
            self._engine_worker = self._make_worker()

        return await self._engine_worker.run(func, args)

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

    @property
    def sync_engine(self):
        """Public property of the underlying SQLAlchemy engine."""
        return self._engine

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
        return _ConnectionContextManager(self._make_async_connection())

    async def _make_async_connection(self):
        worker = self._make_worker()
        try:
            connection = await worker.run(self._engine.connect)
        except Exception:
            await worker.quit()
            raise
        return AsyncConnection(connection, worker, self)

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
        return AsyncResultProxy(rp, self._run_in_thread)

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
            self, schema=None, connection: 'AsyncConnection' = None):
        """Like :meth:`Engine.table_names <sqlalchemy.engine.Engine.table_names>`,
        but is a coroutine.
        """
        run_in_thread = self._run_in_thread

        if connection is not None:
            run_in_thread = connection._run_in_thread
            connection = connection._connection

        return await run_in_thread(self._engine.table_names, schema, connection)

    def run_callable(self, callable_, *args, **kwargs):
        """Like :meth:`Engine.run_callable\
        <sqlalchemy.engine.Engine.run_callable>`.

        .. warning::

            This method blocks. It exists so that we can warn the user if
            they try to use an async engine for table reflection:

            .. code-block:: python

                Table(..., autoload_with=engine)
        """
        warnings.warn(
            'The AsyncEngine has been called in a blocking fashion, e.g. with '
            'Table(..., autoload_with=engine). You may wish to run it in a '
            'separate thread to avoid blocking the event loop. You can use '
            'Table(..., autoload_with=engine.sync_engine) to opt out of the '
            'warning for this blocking behaviour.',
            BlockingWarning)
        self._engine.run_callable(callable_, *args, **kwargs)

    def __repr__(self):
        r = ReprHelper(self)
        r.parantheses = ('<', '>')
        r.positional_from_attr('_engine')
        return str(r)

    def __getattr__(self, item):
        msg = '{!r} object has no attribute {!r}.'.format(
            self.__class__.__name__, item)

        if item == '_run_visitor':
            raise AttributeError(
                msg + ' Did you try to use Table.create(engine) or similar? '
                'You must use Table.create(engine.sync_engine) instead, which'
                'is a blocking function. Consider using sqlalchemy.schema.'
                'CreateTable instead'
            )
        elif item == 'dispatch':
            raise AttributeError(
                msg + ' Did you try to use event.listen(engine, ...)? You must '
                'use event.listen(engine.sync_engine, ...) instead.'
            )

        raise AttributeError(msg)


class AsyncConnection:
    """Mostly like :class:`sqlalchemy.engine.Connection` except some of the
    methods are coroutines.
    """
    def __init__(self, connection, worker, engine):
        self._connection = connection
        self._worker = worker
        self._engine_ref = weakref.ref(engine)

    async def _run_in_thread(_self, _func, *args, **kwargs):
        return await _self._worker.run(_func, args, kwargs)

    async def run_in_thread(self, func, *args):
        """Run a synchronous function in the connection's worker thread.

        Example:
            The following blocking function:

            .. code-block:: python

                some_fn(conn.sync_connection)

            can be called like this instead:

            .. code-block:: python

                await engine.run_in_thread(some_fn, conn.sync_connection)

        Parameters:
            func: A synchronous function.
            args: Positional arguments to be passed to `func`. If you need to
                pass keyword arguments, then use :func:`functools.partial`.
        """
        return await self._worker.run(func, args)

    @property
    def _engine(self):
        return self._engine_ref()

    @property
    def sync_connection(self):
        """Public property of the underlying SQLAlchemy connection."""
        return self._connection

    @property
    def dialect(self):
        return self._connection.dialect

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
        try:
            rp = await self._run_in_thread(
                self._connection.execute, *args, **kwargs)
        except AlreadyQuit:
            raise StatementError("This Connection is closed.", None, None, None)

        return AsyncResultProxy(rp, self._run_in_thread)

    def connect(self):
        """Like :meth:`Connection.connect <sqlalchemy.engine.Connection.connect>`,
        but is a coroutine.
        """
        return _ConnectionContextManager(self._make_async_connection())

    async def _make_async_connection(self):
        worker = self._engine._make_worker(branch_from=self._worker)
        try:
            connection = await worker.run(self._connection.connect)
        except Exception:
            await worker.quit()
            raise
        return AsyncConnection(connection, worker, self._engine)

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
        try:
            res = await self._run_in_thread(
                self._connection.close, *args, **kwargs)
            await self._worker.quit()
        except AlreadyQuit:
            raise StatementError("This Connection is closed.", None, None, None)

        return res

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
        try:
            transaction = await self._run_in_thread(self._connection.begin)
        except AlreadyQuit:
            raise StatementError("This Connection is closed.", None, None, None)

        return AsyncTransaction(transaction, self._run_in_thread)

    def begin_nested(self):
        """Like :meth:`Connection.begin_nested\
        <sqlalchemy.engine.Connection.begin_nested>`, but returns an awaitable
        that can also be used as an asynchronous context manager.

        .. seealso:: :meth:`begin` for examples.
        """
        return _TransactionContextManager(self._begin_nested())

    async def _begin_nested(self):
        try:
            transaction = await self._run_in_thread(self._connection.begin_nested)
        except AlreadyQuit:
            raise StatementError("This Connection is closed.", None, None, None)

        return AsyncTransaction(transaction, self._run_in_thread)

    def in_transaction(self):
        """Like :meth:`Connection.in_transaction\
        <sqlalchemy.engine.Connection.in_transaction>`.
        """
        return self._connection.in_transaction()

    def run_callable(self, callable_, *args, **kwargs):
        """Like :meth:`Connection.run_callable\
        <sqlalchemy.engine.Connection.run_callable>`.

        .. warning::

            This method blocks. It exists so that we can warn the user if
            they try to use an async connection for table reflection:

            .. code-block:: python

                Table(..., autoload_with=connection)
        """
        warnings.warn(
            'The AsyncConnection has been called in a blocking fashion, e.g. '
            'with Table(..., autoload_with=connection). You may wish to run it '
            'in a separate thread to avoid blocking the event loop. You can '
            'use Table(..., autoload_with=connection.sync_connection) to opt '
            'out of the warning for this blocking behaviour.',
            BlockingWarning)
        self._connection.run_callable(callable_, *args, **kwargs)

    def __getattr__(self, item):
        msg = '{!r} object has no attribute {!r}.'.format(
            self.__class__.__name__, item)

        if item == '_run_visitor':
            raise AttributeError(
                msg + ' Did you try to use Table.create(connection) or '
                'similar? You must use Table.create(connection.sync_connection'
                ') instead, which is a blocking function. Consider using '
                'sqlalchemy.schema.CreateTable instead.'
            )
        elif item == 'dispatch':
            raise AttributeError(
                msg + ' Did you try to use event.listen(connection, ...)? You'
                'must use event.listen(connection.sync_connection, ...) instead.'
            )

        raise AttributeError(msg)


class AsyncTransaction:
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


class _AsyncResultProxyIterator:
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


class AsyncResultProxy:
    """Mostly like :class:`sqlalchemy.engine.ResultProxy` except some of the
    methods are coroutines.
    """
    def __init__(self, result_proxy, run_in_thread):
        self._result_proxy = result_proxy
        self._run_in_thread = run_in_thread

    def __aiter__(self):
        return _AsyncResultProxyIterator(
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

    def __enter__(self):
        raise TypeError(
            'Use async with instead. This error can occur when trying to '
            'pass the AsyncEngine to something that expects a normal engine, '
            'e.g. MetaData.reflect(). You can use engine.sync_engine, but be '
            'aware that the function will block. You should run it in a '
            'separate thread. See also connection.sync_connection'
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


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


class _EngineTransactionContextManager:
    __slots__ = ('_engine', '_close_with_result', '_context', '_worker')

    def __init__(self, engine: AsyncEngine, close_with_result):
        self._engine = engine
        self._close_with_result = close_with_result
        self._worker = self._engine._make_worker()

    async def _run_in_thread(_self, _func, *args, **kwargs):
        return await _self._worker.run(_func, args, kwargs)

    async def __aenter__(self):
        self._context = await self._run_in_thread(
            self._engine._engine.begin, self._close_with_result)

        conn = await self._run_in_thread(self._context.__enter__)
        return AsyncConnection(conn, self._worker, self._engine)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._run_in_thread(
            self._context.__exit__, exc_type, exc_val, exc_tb)


class ThreadWorker(ABC):
    @abstractmethod
    async def run(self, func, args=(), kwargs=None):
        raise NotImplementedError

    @abstractmethod
    async def quit(self):
        raise NotImplementedError
