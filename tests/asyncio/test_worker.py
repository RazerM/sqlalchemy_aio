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
