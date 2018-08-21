import pytest

from sqlalchemy_aio import AlreadyQuit


@pytest.mark.trio
async def test_already_quit():
    from sqlalchemy_aio.trio import TrioThreadWorker
    worker = TrioThreadWorker()
    await worker.quit()

    with pytest.raises(AlreadyQuit):
        await worker.run(lambda: None)

    with pytest.raises(AlreadyQuit):
        await worker.quit()
