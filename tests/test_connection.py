import pytest
from sqlalchemy import select
from sqlalchemy.exc import StatementError
from sqlalchemy.schema import CreateTable

from sqlalchemy_aio._base import AsyncTransaction


@pytest.mark.asyncio
async def test_execute(engine):
    conn = await engine.connect()
    result = await conn.execute(select([1]))
    assert await result.scalar() == 1
    await conn.close()


@pytest.mark.asyncio
async def test_scalar(engine):
    async with engine.connect() as conn:
        assert await conn.scalar(select([1])) == 1


@pytest.mark.asyncio
async def test_close(engine):
    conn = await engine.connect()
    assert not conn.closed

    result = await conn.execute(select([1]))
    assert await result.scalar() == 1

    await conn.close()
    assert conn.closed

    with pytest.raises(StatementError) as exc:
        await conn.execute(select([1]))
    assert "This Connection is closed" in str(exc)


@pytest.mark.asyncio
async def test_in_transaction(engine):
    conn = await engine.connect()
    assert not conn.in_transaction()

    trans = await conn.begin()
    assert isinstance(trans, AsyncTransaction)
    assert conn.in_transaction()

    await trans.close()
    assert not conn.in_transaction()

    await conn.close()


@pytest.mark.asyncio
async def test_transaction_commit(engine, mytable):
    async with engine.connect() as conn:
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
async def test_transaction_rollback(engine, mytable):
    async with engine.connect() as conn:
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
async def test_transaction_context_manager_success(engine, mytable):
    async with engine.connect() as conn:
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
async def test_transaction_context_manager_failure(engine, mytable):
    async with engine.connect() as conn:
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
async def test_begin_nested(engine, mytable):
    async with engine.connect() as conn:
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
