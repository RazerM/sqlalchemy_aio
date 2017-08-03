import asyncio

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event

from sqlalchemy_aio import ASYNCIO_STRATEGY


def fix_pysqlite_transactions(engine):
    """See http://docs.sqlalchemy.org/en/latest/dialects/
    sqlite.html#serializable-isolation-savepoints-transactional-ddl
    """

    @event.listens_for(engine, 'connect')
    def connect(dbapi_connection, connection_record):
        # disable pysqlite's emitting of the BEGIN statement entirely.
        # also stops it from emitting COMMIT before any DDL.
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, 'begin')
    def begin(conn):
        # emit our own BEGIN
        conn.execute('BEGIN')


@pytest.fixture
def event_loop(request):
    """Create an asyncio event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def teardown():
        loop.close()

    request.addfinalizer(teardown)

    return loop


@pytest.fixture(params=[True, False], ids=['memory', 'file'])
def engine(request, tmpdir, event_loop):
    # sqlite has different behaviour when used with multiple threads with an
    # in-memory or file database.
    if request.param:
        url = 'sqlite:///:memory:'
    else:
        file = tmpdir.join('test.db')
        url = 'sqlite:///' + str(file)

    engine = create_engine(url, strategy=ASYNCIO_STRATEGY, loop=event_loop)
    fix_pysqlite_transactions(engine._engine)

    return engine


@pytest.fixture
def mytable():
    metadata = MetaData()
    mytable = Table(
        'mytable', metadata,
        Column('id', Integer, primary_key=True),
    )
    return mytable
