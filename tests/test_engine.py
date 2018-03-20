from unittest.mock import Mock, call, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.schema import CreateTable

from sqlalchemy_aio import ASYNCIO_STRATEGY
from sqlalchemy_aio.engine import AsyncioEngine
from sqlalchemy_aio._base import AsyncConnection, AsyncTransaction


def test_create_engine():
    engine = create_engine('sqlite://', strategy=ASYNCIO_STRATEGY)
    assert isinstance(engine, AsyncioEngine)


def test_create_engine_args():
    loop = Mock()

    engine = create_engine('sqlite://', loop=loop, strategy=ASYNCIO_STRATEGY)

    assert engine._loop is loop


@pytest.mark.asyncio
async def test_implicit_loop():
    engine = create_engine('sqlite://', strategy=ASYNCIO_STRATEGY)
    assert await engine.scalar(select([1])) == 1


@pytest.mark.asyncio
async def test_run_in_thread(engine):
    def fn(*args, **kwargs):
        return args, kwargs

    assert await engine._run_in_thread(fn) == ((), {})
    assert await engine._run_in_thread(fn, 1, 2, a=3) == ((1, 2), {'a': 3})
    assert await engine._run_in_thread(fn, 1) == ((1,), {})

    # Test that self is passed to the function rather than consumed by the
    # method.
    assert await engine._run_in_thread(fn, self=1) == ((), {'self': 1})


@pytest.mark.asyncio
async def test_connect(engine):
    conn = await engine.connect()
    assert isinstance(conn, AsyncConnection)
    await conn.close()


@pytest.mark.asyncio
async def test_connect_context_manager(engine):
    async with engine.connect() as conn:
        assert isinstance(conn, AsyncConnection)
    assert conn.closed


@pytest.mark.asyncio
async def test_implicit_transaction_success(engine, mytable):
    async with engine.begin() as conn:
        assert isinstance(conn, AsyncConnection)

        await conn.execute(CreateTable(mytable))
        await conn.execute(mytable.insert())
        result = await conn.execute(mytable.select())
        rows = await result.fetchall()
        assert len(rows) == 1

    # Transaction should have been committed automatically
    result = await engine.execute(mytable.select())
    rows = await result.fetchall()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_implicit_transaction_failure(engine, mytable):
    await engine.execute(CreateTable(mytable))

    with pytest.raises(RuntimeError):
        async with engine.begin() as conn:
            assert isinstance(conn, AsyncConnection)

            await conn.execute(mytable.insert())
            result = await conn.execute(mytable.select())
            rows = await result.fetchall()
            assert len(rows) == 1

            raise RuntimeError

    # Transaction should have been rolled back automatically
    result = await engine.execute(mytable.select())
    rows = await result.fetchall()
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_implicit_transaction_commit_failure(engine, mytable):
    # Patch commit to raise an exception. We can then check that a) the
    # transaction is rolled back, and b) that the exception is reraised.
    patch_commit = patch.object(
        AsyncTransaction, 'commit', side_effect=RuntimeError)

    # Patch a coroutine in place of AsyncioTransaction.rollback that calls
    # a Mock which we can later check.
    mock_rollback = Mock()

    async def mock_coro(*args, **kwargs):
        mock_rollback(*args, **kwargs)

    patch_rollback = patch.object(AsyncTransaction, 'rollback', mock_coro)

    with pytest.raises(RuntimeError):
        with patch_commit, patch_rollback:

            async with engine.connect() as conn:
                await conn.execute(CreateTable(mytable))

                async with conn.begin() as trans:
                    await conn.execute(mytable.insert())

    assert mock_rollback.call_count == 1


@pytest.mark.asyncio
async def test_execute(engine):
    result = await engine.execute(select([1]))
    assert await result.scalar() == 1


@pytest.mark.asyncio
async def test_scalar(engine):
    assert await engine.scalar(select([1])) == 1


@pytest.mark.asyncio
async def test_has_table(engine, mytable):
    assert not await engine.has_table('mytable')
    await engine.execute(CreateTable(mytable))
    assert await engine.has_table('mytable')


@pytest.mark.asyncio
async def test_table_names(engine, mytable):
    assert await engine.table_names() == []
    await engine.execute(CreateTable(mytable))
    assert await engine.table_names() == ['mytable']


@pytest.mark.asyncio
async def test_table_names_with_connection(engine, mytable):
    conn = await engine.connect()

    # spy on connection to make sure .execute is called
    patch_conn = patch.object(conn, '_connection', wraps=conn._connection)

    with patch_conn as mock_conn:
        assert await engine.table_names(connection=conn) == []
        await conn.execute(CreateTable(mytable))
        assert await engine.table_names(connection=conn) == ['mytable']
        assert mock_conn.execute.called

    await conn.close()


def test_repr():
    engine = create_engine('sqlite://', strategy=ASYNCIO_STRATEGY)
    assert repr(engine) == 'AsyncioEngine<Engine(sqlite://)>'


def test_engine_keywords():
    # SQLAlchemy checks which keywords AsyncioEngine expects, so check that
    # echo, logging_name, and execution_options are accepted and then passed on
    # by AsyncioEngine.

    with patch('sqlalchemy_aio._base.Engine') as mock_engine:
        create_engine('sqlite://', strategy=ASYNCIO_STRATEGY, echo=True,
                      logging_name='myengine', execution_options=dict())

        kwargs = mock_engine.call_args[1]
        assert {'echo', 'logging_name', 'execution_options'} <= set(kwargs)


def test_logger(engine):
    assert engine.logger
