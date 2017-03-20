sqlalchemy_aio
==============

|PyPI Version| |Documentation| |Travis| |Coverage| |MIT License|

``sqlalchemy_aio`` adds asyncio support to SQLAlchemy core, derived from
`alchimia`_.

.. _alchimia: https://github.com/alex/alchimia


Getting started
---------------

.. code-block:: python

    import asyncio

    from sqlalchemy_aio import ASYNCIO_STRATEGY

    from sqlalchemy import (
        Column, Integer, MetaData, Table, Text, create_engine, select)
    from sqlalchemy.schema import CreateTable, DropTable


    async def main():
        engine = create_engine(
            # In-memory sqlite database cannot be accessed from different
            # threads, use file.
            'sqlite:///test.db', strategy=ASYNCIO_STRATEGY
        )

        metadata = MetaData()
        users = Table(
            'users', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', Text),
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
                assert await conn.scalar(select([1])) == 1

        await engine.execute(DropTable(users))


    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())


.. |PyPI Version| image:: https://img.shields.io/pypi/v/sqlalchemy_aio.svg?style=flat-square
   :target: https://pypi.python.org/pypi/sqlalchemy_aio/
.. |Documentation| image:: https://img.shields.io/badge/docs-latest-brightgreen.svg?style=flat-square
   :target: https://sqlalchemy-aio.readthedocs.io/en/latest/
.. |Travis| image:: http://img.shields.io/travis/RazerM/sqlalchemy_aio/master.svg?style=flat-square&label=travis
   :target: https://travis-ci.org/RazerM/sqlalchemy_aio
.. |Coverage| image:: https://img.shields.io/codecov/c/github/RazerM/sqlalchemy_aio/master.svg?style=flat-square
   :target: https://codecov.io/github/RazerM/sqlalchemy_aio?branch=master
.. |MIT License| image:: http://img.shields.io/badge/license-MIT-blue.svg?style=flat-square
   :target: https://raw.githubusercontent.com/RazerM/sqlalchemy_aio/master/LICENSE
