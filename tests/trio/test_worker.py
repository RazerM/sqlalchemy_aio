import pytest

from sqlalchemy_aio import AlreadyQuit
from sqlalchemy_aio.trio import TrioThreadWorker

@pytest.mark.trio
async def test_already_quit():
    worker = TrioThreadWorker()
    await worker.quit()

    with pytest.raises(AlreadyQuit):
        await worker.run(lambda: None)

    with pytest.raises(AlreadyQuit):
        await worker.quit()
