import pytest
from sqlalchemy import func, select
from sqlalchemy.schema import CreateTable

from sqlalchemy_aio.engine import AsyncioResultProxy


@pytest.mark.asyncio
async def test_result_proxy(engine):
    result = await engine.execute(select([1]))
    assert isinstance(result, AsyncioResultProxy)
    await result.close()


@pytest.mark.asyncio
async def test_fetchone(engine):
    result = await engine.execute(select([1]))
    assert await result.fetchone() == (1,)
    await result.close()


@pytest.mark.asyncio
async def test_fetchall(engine):
    result = await engine.execute(select([1]))
    assert await result.fetchall() == [(1,)]


@pytest.mark.asyncio
async def test_scalar(engine):
    result = await engine.execute(select([1]))
    assert await result.scalar() == 1


@pytest.mark.asyncio
async def test_first(engine):
    result = await engine.execute(select([1]))
    assert await result.first() == (1,)
    await result.close()


@pytest.mark.asyncio
async def test_keys(engine):
    result = await engine.execute(select([func.now().label('time')]))
    assert await result.keys() == ['time']
    await result.close()


@pytest.mark.asyncio
async def test_returns_rows(engine, mytable):
    result = await engine.execute(select([1]))
    assert result.returns_rows
    await result.close()
    result = await engine.execute(CreateTable(mytable))
    assert not result.returns_rows
    await result.close()


@pytest.mark.asyncio
async def test_rowcount(engine, mytable):
    await engine.execute(CreateTable(mytable))
    await engine.execute(mytable.insert())
    await engine.execute(mytable.insert())
    result = await engine.execute(mytable.delete())
    assert result.rowcount == 2


@pytest.mark.asyncio
async def test_inserted_primary_key(engine, mytable):
    await engine.execute(CreateTable(mytable))
    result = await engine.execute(mytable.insert())
    assert result.inserted_primary_key == [1]
