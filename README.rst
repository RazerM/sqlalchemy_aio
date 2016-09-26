sqlalchemy_aio
==============

``sqlalchemy_aio`` adds asyncio support to SQLAlchemy core, derived from
`alchimia`_.

.. _alchimia: https://github.com/alex/alchimia


Getting started
---------------

.. code-block:: python

    import asyncio

    from sqlalchemy_aio import ASYNCIO_STRATEGY

    from sqlalchemy import (
        MetaData, Table, Column, Integer, String, create_engine, select)
    from sqlalchemy.schema import CreateTable

    async def main():
        engine = create_engine(
            'sqlite://', strategy=ASYNCIO_STRATEGY
        )

        metadata = MetaData()
        users = Table('users', metadata,
            Column('id', Integer(), primary_key=True),
            Column('name', String()),
        )

        # Create the table
        await engine.execute(CreateTable(users))

        conn = await engine.connect()

        # Insert some users
        await conn.execute(users.insert().values(name='Jeremy Goodwin'))
        await conn.execute(users.insert().values(name='Natalie Hurley'))
        await conn.execute(users.insert().values(name='Dan Rydell'))
        await conn.execute(users.insert().values(name='Casey McCall'))
        await conn.execute(users.insert().values(name='Dana Whitaker'))

        result = await conn.execute(users.select(users.c.name.startswith('D')))
        d_users = await result.fetchall()

        await conn.close()

        # Print out the users
        for user in d_users:
            print('Username: %s' % user[users.c.name])

        # Supports context async managers
        async with engine.connect() as conn:
            async with conn.begin() as trans:
                r = await conn.execute(select([1]))
                assert await r.fetchone() == (1,)

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
