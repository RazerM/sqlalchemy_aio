from contextlib import suppress

import pytest
from sqlalchemy import MetaData, Table, event, select
from sqlalchemy.exc import NoSuchTableError, StatementError
from sqlalchemy.schema import CreateTable

from sqlalchemy_aio.base import AsyncTransaction
from sqlalchemy_aio.exc import BlockingWarning

pytestmark = pytest.mark.noextras


@pytest.mark.asyncio
async def test_execute(asyncio_engine):
    conn = await asyncio_engine.connect()
    result = await conn.execute(select([1]))
    assert await result.scalar() == 1
    await conn.close()


@pytest.mark.asyncio
async def test_scalar(asyncio_engine):
    async with asyncio_engine.connect() as conn:
        assert await conn.scalar(select([1])) == 1


@pytest.mark.asyncio
async def test_close(asyncio_engine):
    conn = await asyncio_engine.connect()
    assert not conn.closed

    result = await conn.execute(select([1]))
    assert await result.scalar() == 1

    await conn.close()
    assert conn.closed

    with pytest.raises(StatementError, match='This Connection is closed'):
        await conn.close()

    with pytest.raises(StatementError, match='This Connection is closed'):
        await conn.execute(select([1]))

    with pytest.raises(StatementError, match='This Connection is closed'):
        await conn.begin()

    with pytest.raises(StatementError, match='This Connection is closed'):
        await conn.begin_nested()


@pytest.mark.asyncio
async def test_in_transaction(asyncio_engine):
    conn = await asyncio_engine.connect()
    assert not conn.in_transaction()

    trans = await conn.begin()
    assert isinstance(trans, AsyncTransaction)
    assert conn.in_transaction()

    await trans.close()
    assert not conn.in_transaction()

    await conn.close()


@pytest.mark.asyncio
async def test_transaction_commit(asyncio_engine, mytable):
    async with asyncio_engine.connect() as conn:
        trans = await conn.begin()
        await conn.execute(CreateTable(mytable))
        await conn.execute(mytable.insert())

        result = await conn.execute(mytable.select())
        rows = await result.fetchall()
        assert len(rows) == 1

        await trans.commit()

        result = await conn.execute(mytable.select())
        rows = await result.fetchall()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_transaction_rollback(asyncio_engine, mytable):
    async with asyncio_engine.connect() as conn:
        await conn.execute(CreateTable(mytable))

        trans = await conn.begin()
        await conn.execute(mytable.insert())

        result = await conn.execute(mytable.select())
        rows = await result.fetchall()
        assert len(rows) == 1

        await trans.rollback()

        result = await conn.execute(mytable.select())
        rows = await result.fetchall()
        assert len(rows) == 0


@pytest.mark.asyncio
async def test_transaction_context_manager_success(asyncio_engine, mytable):
    async with asyncio_engine.connect() as conn:
        await conn.execute(CreateTable(mytable))

        async with conn.begin() as trans:
            await conn.execute(mytable.insert())

            result = await conn.execute(mytable.select())
            rows = await result.fetchall()
            assert len(rows) == 1

        result = await conn.execute(mytable.select())
        rows = await result.fetchall()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_transaction_context_manager_failure(asyncio_engine, mytable):
    async with asyncio_engine.connect() as conn:
        await conn.execute(CreateTable(mytable))

        with pytest.raises(RuntimeError):
            async with conn.begin() as trans:
                await conn.execute(mytable.insert())

                result = await conn.execute(mytable.select())
                rows = await result.fetchall()
                assert len(rows) == 1

                raise RuntimeError

        result = await conn.execute(mytable.select())
        rows = await result.fetchall()
        assert len(rows) == 0


@pytest.mark.asyncio
async def test_begin_nested(asyncio_engine, mytable):
    async with asyncio_engine.connect() as conn:
        await conn.execute(CreateTable(mytable))

        async with conn.begin() as trans1:
            await conn.execute(mytable.insert())

            async with conn.begin_nested() as trans2:
                assert isinstance(trans2, AsyncTransaction)
                await conn.execute(mytable.insert())
                await trans2.rollback()

            await trans1.commit()

        result = await conn.execute(mytable.select())
        rows = await result.fetchall()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_run_callable_warning(asyncio_engine):
    meta = MetaData()
    thread_called = False

    # we must use sqlite connections in the same thread they were created in,
    # hence the indirection here.

    def thread_fn(conn):
        nonlocal thread_called

        with pytest.warns(BlockingWarning, match='sync_connection') as record:
            with suppress(NoSuchTableError):
                Table('sometable', meta, autoload_with=conn)

        assert len(record) == 1

        with pytest.warns(None) as record:
            with suppress(NoSuchTableError):
                Table('sometable', meta, autoload_with=conn.sync_connection)

        assert len(record) == 0

        thread_called = True

    async with asyncio_engine.connect() as conn:
        await conn.run_in_thread(thread_fn, conn)
        assert thread_called


@pytest.mark.asyncio
async def test_run_visitor_exception(asyncio_engine, mytable):
    thread_called = False

    def thread_fn(conn):
        nonlocal thread_called

        with pytest.raises(AttributeError, match='Did you try to use'):
            mytable.create(conn)

        mytable.create(conn.sync_connection)

        thread_called = True

    async with asyncio_engine.connect() as conn:
        await conn.run_in_thread(thread_fn, conn)
        assert thread_called


@pytest.mark.asyncio
async def test_sync_cm_exception(asyncio_engine):
    thread_called = False

    def thread_fn(conn):
        nonlocal thread_called

        meta = MetaData()
        with pytest.raises(TypeError, match='Use async with'):
            meta.reflect(conn)

        meta.reflect(conn.sync_connection)

        thread_called = True

    async with asyncio_engine.connect() as conn:
        await conn.run_in_thread(thread_fn, conn)
        assert thread_called


@pytest.mark.asyncio
async def test_event_listen_exception(asyncio_engine):
    async with asyncio_engine.connect() as conn:
        with pytest.raises(AttributeError, match='Did you try to use'):
            event.listen(conn, 'connect', None)


@pytest.mark.asyncio
async def test_connection_connect(asyncio_engine):
    async with asyncio_engine.connect() as conn1:
        assert await conn1.scalar(select([1])) == 1
        async with conn1.connect() as conn2:
            assert await conn2.scalar(select([1])) == 1

        assert not conn1.closed
        assert conn2.closed
        assert not conn1._worker._has_quit
        assert conn2._worker._has_quit

    assert conn1.closed
    assert conn1._worker._has_quit


@pytest.mark.asyncio
async def test_attribute_error(asyncio_engine):
    async with asyncio_engine.connect() as conn:
        with pytest.raises(AttributeError):
            conn.spam
