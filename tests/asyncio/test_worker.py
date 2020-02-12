import asyncio
import pytest

from sqlalchemy_aio import AlreadyQuit
from sqlalchemy_aio.asyncio import AsyncioThreadWorker


@pytest.mark.asyncio
async def test_already_quit():
    worker = AsyncioThreadWorker()
    await worker.quit()

    with pytest.raises(AlreadyQuit):
        await worker.run(lambda: None)

    with pytest.raises(AlreadyQuit):
        await worker.quit()


@pytest.mark.asyncio
async def test_interrupted_run():
    worker = AsyncioThreadWorker()

    loop = asyncio.get_event_loop()
    event = asyncio.Event()

    async def set_event():
        event.set()

    def returns_number(number):
        asyncio.run_coroutine_threadsafe(set_event(), loop)
        return number

    task = asyncio.ensure_future(worker.run(returns_number, [2]))
    await event.wait()
    task.cancel()
    value = await worker.run(returns_number, [3])
    assert 3 == value
    await worker.quit()
