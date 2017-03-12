sqlalchemy_aio
==============

What is this?
-------------

It's *not* an ``asyncio`` implementation of SQLAlchemy or the drivers it uses.
``sqlalchemy_aio`` lets you use SQLAlchemy by running operations in a separate
thread.

If you're already using :meth:`run_in_executor` to execute SQLAlchemy tasks,
``sqlalchemy_aio`` will work well with similar performance. If performance is
critical, perhaps `asyncpg`_ can help.

.. _asyncpg: https://github.com/MagicStack/asyncpg

Threading Model
---------------

Explicit connections (:meth:`engine.connect()\
<sqlalchemy_aio.engine.AsyncioEngine.connect>`) each run in their own thread.
For implicit connections (e.g. :meth:`engine.execute()\
<sqlalchemy_aio.engine.AsyncioEngine.execute>`), the engine may use multiple
threads as long as the DBAPI is thread safe (the SQLite DBAPI is not).

Getting started
---------------

.. code-block:: python

    from sqlalchemy_aio import ASYNCIO_STRATEGY

    from sqlalchemy import (
        Column, Integer, MetaData, Table, Text, create_engine)
    from sqlalchemy.schema import CreateTable


    async def main():
        engine = create_engine('sqlite://', strategy=ASYNCIO_STRATEGY)

        metadata = MetaData()
        users = Table(
            'users', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', Text),
        )

        # Create the table
        await engine.execute(CreateTable(users))

        conn = await engine.connect()

        # Supports usual context managers
        async with conn.begin() as trans:
            # Insert some users
            await conn.execute(users.insert().values(name='Jeremy Goodwin'))
            await conn.execute(users.insert().values(name='Natalie Hurley'))
            await conn.execute(users.insert().values(name='Dan Rydell'))
            await conn.execute(users.insert().values(name='Casey McCall'))
            await conn.execute(users.insert().values(name='Dana Whitaker'))

        await conn.close()

        # Connection context manager
        async with engine.connect() as conn:
            result = await conn.execute(users.select(users.c.name.startswith('D')))
            d_users = await result.fetchall()

        # Print out the users
        for user in d_users:
            print('Username: %s' % user[users.c.name])

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())


Contents
========

.. toctree::
    :maxdepth: 2

    ddl
    api-reference
    limitations
    contributing



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
