import pytest
from sqlalchemy import func, select
from sqlalchemy.schema import CreateTable

from sqlalchemy_aio.base import AsyncResultProxy

pytestmark = pytest.mark.noextras


@pytest.mark.asyncio
async def test_result_proxy(asyncio_engine):
    result = await asyncio_engine.execute(select([1]))
    assert isinstance(result, AsyncResultProxy)
    await result.close()


@pytest.mark.asyncio
async def test_fetchone(asyncio_engine):
    result = await asyncio_engine.execute(select([1]))
    assert await result.fetchone() == (1,)
    await result.close()


@pytest.mark.asyncio
async def test_fetchmany_value(asyncio_engine):
    result = await asyncio_engine.execute(select([1]))
    assert await result.fetchmany() == [(1,)]
    await result.close()


@pytest.mark.asyncio
async def test_fetchmany_quantity(asyncio_engine, mytable):
    await asyncio_engine.execute(CreateTable(mytable))
    await asyncio_engine.execute(mytable.insert())
    await asyncio_engine.execute(mytable.insert())
    result = await asyncio_engine.execute(select([mytable]))
    rows = await result.fetchmany(1)
    assert len(rows) == 1
    await result.close()
    await asyncio_engine.execute(mytable.delete())


@pytest.mark.asyncio
async def test_fetchmany_all(asyncio_engine, mytable):
    await asyncio_engine.execute(CreateTable(mytable))
    await asyncio_engine.execute(mytable.insert())
    await asyncio_engine.execute(mytable.insert())
    await asyncio_engine.execute(mytable.insert())
    result = await asyncio_engine.execute(select([mytable]))
    rows = await result.fetchmany(100)
    assert len(rows) == 3
    await result.close()
    await asyncio_engine.execute(mytable.delete())


@pytest.mark.asyncio
async def test_fetchall(asyncio_engine):
    result = await asyncio_engine.execute(select([1]))
    assert await result.fetchall() == [(1,)]


@pytest.mark.asyncio
async def test_scalar(asyncio_engine):
    result = await asyncio_engine.execute(select([1]))
    assert await result.scalar() == 1


@pytest.mark.asyncio
async def test_first(asyncio_engine):
    result = await asyncio_engine.execute(select([1]))
    assert await result.first() == (1,)
    await result.close()


@pytest.mark.asyncio
async def test_keys(asyncio_engine):
    result = await asyncio_engine.execute(select([func.now().label('time')]))
    assert await result.keys() == ['time']
    await result.close()


@pytest.mark.asyncio
async def test_returns_rows(asyncio_engine, mytable):
    result = await asyncio_engine.execute(select([1]))
    assert result.returns_rows
    await result.close()
    result = await asyncio_engine.execute(CreateTable(mytable))
    assert not result.returns_rows
    await result.close()


@pytest.mark.asyncio
async def test_rowcount(asyncio_engine, mytable):
    await asyncio_engine.execute(CreateTable(mytable))
    await asyncio_engine.execute(mytable.insert())
    await asyncio_engine.execute(mytable.insert())
    result = await asyncio_engine.execute(mytable.delete())
    assert result.rowcount == 2


@pytest.mark.asyncio
async def test_inserted_primary_key(asyncio_engine, mytable):
    await asyncio_engine.execute(CreateTable(mytable))
    result = await asyncio_engine.execute(mytable.insert())
    assert result.inserted_primary_key == [1]


@pytest.mark.asyncio
async def test_aiter(asyncio_engine, mytable):
    await asyncio_engine.execute(CreateTable(mytable))
    await asyncio_engine.execute(mytable.insert())
    await asyncio_engine.execute(mytable.insert())
    result = await asyncio_engine.execute(select([mytable]))
    fetched = []
    async for row in result:
        fetched.append(row)
    await asyncio_engine.execute(mytable.delete())
    assert len(fetched) == 2
