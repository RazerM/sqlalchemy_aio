DDL
===

Because of some of the limitations in the SQLAlchemy API, it’s not possible to
asynchronously create tables using :meth:`sqlalchemy.schema.Table.create` or
:meth:`sqlalchemy.schema.MetaData.create_all`.

Instead of:

.. code-block:: python

    users = Table('users', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String),
    )

    users.create(engine)


you can use :class:`sqlalchemy.schema.CreateTable` or
:meth:`AsyncEngine.run_in_thread`:

.. code-block:: python

    await engine.execute(CreateTable(users))

.. code-block:: python

    await engine.run_in_thread(users.create, engine.sync_engine)


For :meth:`MetaData.create_all() <sqlalchemy.schema.MetaData.create_all>`,
instead of:

.. code-block:: python

    metadata.create_all(engine)

you have to do:

.. code-block:: python

    await engine.run_in_thread(metadata.create_all, engine.sync_engine)
