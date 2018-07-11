import pytest
from sqlalchemy import func, select
from sqlalchemy.schema import CreateTable

from sqlalchemy_aio.base import AsyncResultProxy


@pytest.mark.trio
async def test_result_proxy(trio_engine):
    result = await trio_engine.execute(select([1]))
    assert isinstance(result, AsyncResultProxy)
    await result.close()


@pytest.mark.trio
async def test_fetchone(trio_engine):
    result = await trio_engine.execute(select([1]))
    assert await result.fetchone() == (1,)
    await result.close()


@pytest.mark.trio
async def test_fetchmany_value(trio_engine):
    result = await trio_engine.execute(select([1]))
    assert await result.fetchmany() == [(1,)]
    await result.close()


@pytest.mark.trio
async def test_fetchmany_quantity(trio_engine, mytable):
    await trio_engine.execute(CreateTable(mytable))
    await trio_engine.execute(mytable.insert())
    await trio_engine.execute(mytable.insert())
    result = await trio_engine.execute(select([mytable]))
    rows = await result.fetchmany(1)
    assert len(rows) == 1
    await result.close()
    await trio_engine.execute(mytable.delete())


@pytest.mark.trio
async def test_fetchmany_all(trio_engine, mytable):
    await trio_engine.execute(CreateTable(mytable))
    await trio_engine.execute(mytable.insert())
    await trio_engine.execute(mytable.insert())
    await trio_engine.execute(mytable.insert())
    result = await trio_engine.execute(select([mytable]))
    rows = await result.fetchmany(100)
    assert len(rows) == 3
    await result.close()
    await trio_engine.execute(mytable.delete())


@pytest.mark.trio
async def test_fetchall(trio_engine):
    result = await trio_engine.execute(select([1]))
    assert await result.fetchall() == [(1,)]


@pytest.mark.trio
async def test_scalar(trio_engine):
    result = await trio_engine.execute(select([1]))
    assert await result.scalar() == 1


@pytest.mark.trio
async def test_first(trio_engine):
    result = await trio_engine.execute(select([1]))
    assert await result.first() == (1,)
    await result.close()


@pytest.mark.trio
async def test_keys(trio_engine):
    result = await trio_engine.execute(select([func.now().label('time')]))
    assert await result.keys() == ['time']
    await result.close()


@pytest.mark.trio
async def test_returns_rows(trio_engine, mytable):
    result = await trio_engine.execute(select([1]))
    assert result.returns_rows
    await result.close()
    result = await trio_engine.execute(CreateTable(mytable))
    assert not result.returns_rows
    await result.close()


@pytest.mark.trio
async def test_rowcount(trio_engine, mytable):
    await trio_engine.execute(CreateTable(mytable))
    await trio_engine.execute(mytable.insert())
    await trio_engine.execute(mytable.insert())
    result = await trio_engine.execute(mytable.delete())
    assert result.rowcount == 2


@pytest.mark.trio
async def test_inserted_primary_key(trio_engine, mytable):
    await trio_engine.execute(CreateTable(mytable))
    result = await trio_engine.execute(mytable.insert())
    assert result.inserted_primary_key == [1]


@pytest.mark.trio
async def test_aiter(trio_engine, mytable):
    await trio_engine.execute(CreateTable(mytable))
    await trio_engine.execute(mytable.insert())
    await trio_engine.execute(mytable.insert())
    result = await trio_engine.execute(select([mytable]))
    fetched = []
    async for row in result:
        fetched.append(row)
    await trio_engine.execute(mytable.delete())
    assert len(fetched) == 2
