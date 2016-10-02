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
def engine(event_loop):
    engine = create_engine('sqlite://', strategy=ASYNCIO_STRATEGY,
                           loop=event_loop)
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
