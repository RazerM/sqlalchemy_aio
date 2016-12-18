DDL
===

Because of some of the limitations in the SQLAlchemy API, it’s not possible to
create tables using :meth:`sqlalchemy.schema.Table.create` or
:meth:`sqlalchemy.schema.MetaData.create_all`. Luckily, SQLAlchemy provides an
API that still makes it possible to create tables and perform other DDL
operations.

Instead of:

.. code-block:: python

    users = Table('users', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String),
    )

    users.create(engine)

or

.. code-block:: python

    metadata.create_all()

You can use :class:`sqlalchemy.schema.CreateTable`.
