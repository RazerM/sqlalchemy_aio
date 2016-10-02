from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.schema import CreateTable

from sqlalchemy_aio import ASYNCIO_STRATEGY
from sqlalchemy_aio.engine import AsyncioConnection, AsyncioEngine


def test_create_engine():
    engine = create_engine('sqlite://', strategy=ASYNCIO_STRATEGY)
    assert isinstance(engine, AsyncioEngine)


@pytest.mark.asyncio
async def test_connect(engine):
    conn = await engine.connect()
    assert isinstance(conn, AsyncioConnection)
    await conn.close()


@pytest.mark.asyncio
async def test_connect_context_manager(engine):
    async with engine.connect() as conn:
        assert isinstance(conn, AsyncioConnection)
    assert conn.closed


@pytest.mark.asyncio
async def test_implicit_transaction_success(engine, mytable):
    async with engine.begin() as conn:
        assert isinstance(conn, AsyncioConnection)

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
            assert isinstance(conn, AsyncioConnection)

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
async def test_execute(engine):
    result = await engine.execute(select([1]))
    assert await result.scalar() == 1


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
        await engine.execute(CreateTable(mytable))
        assert await engine.table_names(connection=conn) == ['mytable']
        assert mock_conn.execute.called

    await conn.close()


def test_repr(engine):
    assert repr(engine) == 'AsyncioEngine<Engine(sqlite://)>'
