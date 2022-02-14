import warnings
from contextlib import suppress
from functools import partial
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import MetaData, Table, create_engine, event, select
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.schema import CreateTable

from sqlalchemy_aio import ASYNCIO_STRATEGY
from sqlalchemy_aio.asyncio import AsyncioEngine
from sqlalchemy_aio.base import AsyncConnection, AsyncTransaction
from sqlalchemy_aio.exc import BlockingWarning

pytestmark = pytest.mark.noextras


def test_create_engine():
    engine = create_engine('sqlite://', strategy=ASYNCIO_STRATEGY)
    assert isinstance(engine, AsyncioEngine)


@pytest.mark.asyncio
async def test_implicit_loop():
    engine = create_engine('sqlite://', strategy=ASYNCIO_STRATEGY)
    assert await engine.scalar(select([1])) == 1


@pytest.mark.asyncio
async def test_run_in_thread(asyncio_engine):
    def fn(*args, **kwargs):
        return args, kwargs

    assert await asyncio_engine._run_in_thread(fn) == ((), {})
    assert await asyncio_engine._run_in_thread(fn, 1, 2, a=3) == ((1, 2), {'a': 3})
    assert await asyncio_engine._run_in_thread(fn, 1) == ((1,), {})

    # Test that self is passed to the function rather than consumed by the
    # method.
    assert await asyncio_engine._run_in_thread(fn, self=1) == ((), {'self': 1})


@pytest.mark.asyncio
async def test_connect(asyncio_engine):
    conn = await asyncio_engine.connect()
    assert isinstance(conn, AsyncConnection)
    await conn.close()


@pytest.mark.asyncio
async def test_connect_context_manager(asyncio_engine):
    async with asyncio_engine.connect() as conn:
        assert isinstance(conn, AsyncConnection)
    assert conn.closed


@pytest.mark.asyncio
async def test_implicit_transaction_success(asyncio_engine, mytable):
    if ':memory:' in str(asyncio_engine.sync_engine.url):
        pytest.skip(":memory: connections don't persist across threads")

    async with asyncio_engine.begin() as conn:
        assert isinstance(conn, AsyncConnection)

        await conn.execute(CreateTable(mytable))
        await conn.execute(mytable.insert())
        result = await conn.execute(mytable.select())
        rows = await result.fetchall()
        assert len(rows) == 1

    # Transaction should have been committed automatically
    result = await asyncio_engine.execute(mytable.select())
    rows = await result.fetchall()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_implicit_transaction_failure(asyncio_engine, mytable):
    if ':memory:' in str(asyncio_engine.sync_engine.url):
            pytest.skip(":memory: connections don't persist across threads")

    await asyncio_engine.execute(CreateTable(mytable))

    with pytest.raises(RuntimeError):
        async with asyncio_engine.begin() as conn:
            assert isinstance(conn, AsyncConnection)

            await conn.execute(mytable.insert())
            result = await conn.execute(mytable.select())
            rows = await result.fetchall()
            assert len(rows) == 1

            raise RuntimeError

    # Transaction should have been rolled back automatically
    result = await asyncio_engine.execute(mytable.select())
    rows = await result.fetchall()
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_implicit_transaction_commit_failure(asyncio_engine, mytable):
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

            async with asyncio_engine.connect() as conn:
                await conn.execute(CreateTable(mytable))

                async with conn.begin() as trans:
                    await conn.execute(mytable.insert())

    assert mock_rollback.call_count == 1


@pytest.mark.asyncio
async def test_execute(asyncio_engine):
    result = await asyncio_engine.execute(select([1]))
    assert await result.scalar() == 1


@pytest.mark.asyncio
async def test_scalar(asyncio_engine):
    assert await asyncio_engine.scalar(select([1])) == 1


@pytest.mark.asyncio
async def test_has_table(asyncio_engine, mytable):
    assert not await asyncio_engine.has_table('mytable')
    await asyncio_engine.execute(CreateTable(mytable))
    assert await asyncio_engine.has_table('mytable')


@pytest.mark.asyncio
async def test_table_names(asyncio_engine, mytable):
    assert await asyncio_engine.table_names() == []
    await asyncio_engine.execute(CreateTable(mytable))
    assert await asyncio_engine.table_names() == ['mytable']


@pytest.mark.asyncio
async def test_table_names_with_connection(asyncio_engine, mytable):
    conn = await asyncio_engine.connect()

    # spy on connection to make sure .execute is called
    patch_conn = patch.object(conn, '_connection', wraps=conn._connection)

    with patch_conn as mock_conn:
        assert await asyncio_engine.table_names(connection=conn) == []
        await conn.execute(CreateTable(mytable))
        assert await asyncio_engine.table_names(connection=conn) == ['mytable']
        assert mock_conn.execute.called

    await conn.close()


def test_repr():
    asyncio_engine = create_engine('sqlite://', strategy=ASYNCIO_STRATEGY)
    assert repr(asyncio_engine) == 'AsyncioEngine<Engine(sqlite://)>'


def test_engine_keywords():
    # SQLAlchemy checks which keywords AsyncioEngine expects, so check that
    # echo, logging_name, and execution_options are accepted and then passed on
    # by AsyncioEngine.

    with patch('sqlalchemy_aio.base.Engine') as mock_engine:
        create_engine('sqlite://', strategy=ASYNCIO_STRATEGY, echo=True,
                      logging_name='myengine', execution_options=dict())

        kwargs = mock_engine.call_args[1]
        assert {'echo', 'logging_name', 'execution_options'} <= set(kwargs)


def test_logger(asyncio_engine):
    assert asyncio_engine.logger


@pytest.mark.asyncio
async def test_echo(capsys):
    asyncio_engine = create_engine(
        'sqlite://', strategy=ASYNCIO_STRATEGY, echo=True)
    await asyncio_engine.scalar(select([98465]))
    captured = capsys.readouterr()
    assert '98465' in captured.out


@pytest.mark.asyncio
async def test_run_callable_warning(asyncio_engine):
    meta = MetaData()
    with pytest.warns(BlockingWarning, match='sync_engine') as record:
        with suppress(NoSuchTableError):
            Table('sometable', meta, autoload_with=asyncio_engine)

    assert len(record) == 1

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        with suppress(NoSuchTableError):
            Table('sometable', meta, autoload_with=asyncio_engine.sync_engine)


@pytest.mark.asyncio
async def test_run_visitor_exception(asyncio_engine, mytable):
    with pytest.raises(AttributeError, match='Did you try to use'):
        mytable.create(asyncio_engine)

    mytable.create(asyncio_engine.sync_engine)


@pytest.mark.asyncio
async def test_sync_cm_exception(asyncio_engine):
    meta = MetaData()
    with warnings.catch_warnings():
        # ignore warning caused by creating a runtime that is never awaited
        warnings.simplefilter('ignore', RuntimeWarning)
        with pytest.raises(TypeError, match='Use async with'):
            meta.reflect(asyncio_engine)

    meta.reflect(asyncio_engine.sync_engine)


@pytest.mark.asyncio
async def test_event_listen_exception(asyncio_engine):
    with pytest.raises(AttributeError, match='Did you try to use'):
        event.listen(asyncio_engine, 'connect', None)


@pytest.mark.asyncio
async def test_public_run_in_thread(asyncio_engine):
    def fn(*args, **kwargs):
        return args, kwargs

    pfn = partial(fn, 1, 2, a=3)

    assert await asyncio_engine.run_in_thread(pfn) == ((1, 2), {'a': 3})
    assert await asyncio_engine.run_in_thread(fn, 1) == ((1,), {})

    # doesn't accept kwargs
    with pytest.raises(TypeError):
        await asyncio_engine.run_in_thread(fn, a=1)


def test_attribute_error(asyncio_engine):
    with pytest.raises(AttributeError):
        asyncio_engine.spam
