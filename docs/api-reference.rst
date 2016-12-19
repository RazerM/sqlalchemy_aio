API Reference
=============

..
    The contents of this file can be replaced with api-reference.rst.autodoc
    once readthedocs has Python 3.5 builders.

    See https://github.com/rtfd/readthedocs.org/issues/1990

.. currentmodule:: sqlalchemy_aio.engine

.. py:class:: AsyncioEngine(pool, dialect, url, logging_name=None, echo=None, execution_options=None, loop=None, executor=None, **kwargs)
   :module: sqlalchemy_aio.engine

   Mostly like :class:`sqlalchemy.engine.Engine` except some of the methods
   are coroutines.


   .. py:method:: AsyncioEngine.begin(close_with_result=False)
      :module: sqlalchemy_aio.engine

      Like :meth:`Engine.begin <sqlalchemy.engine.Engine.begin>`, but
      returns an asynchronous context manager.

      .. rubric:: Example

      .. code-block:: python

          async with engine.begin():
              await engine.execute(...)


   .. py:method:: AsyncioEngine.connect()
      :module: sqlalchemy_aio.engine

      Like :meth:`Engine.connect <sqlalchemy.engine.Engine.connect>`, but
      returns an awaitable that can also be used as an asynchronous context
      manager.

      .. rubric:: Examples

      .. code-block:: python

          conn = await engine.connect()
          await conn.execute(...)
          await conn.close()

      .. code-block:: python

          async with engine.connect() as conn:
              await conn.execute(...)


   .. py:method:: AsyncioEngine.execute(*args, **kwargs)
      :module: sqlalchemy_aio.engine

      Like :meth:`Engine.execute <sqlalchemy.engine.Engine.execute>`, but
      is a coroutine that returns an :class:`AsyncioResultProxy`.

      .. rubric:: Example

      .. code-block:: python

          result = await engine.execute(...)
          data = await result.fetchall()

      .. warning::

          Make sure to explicitly call :meth:`AsyncioResultProxy.close` if the
          :class:`~sqlalchemy.engine.ResultProxy` has pending rows remaining
          otherwise it will be closed during garbage collection. With SQLite,
          this will raise an exception since the DBAPI connection was created
          in a different thread.


   .. py:method:: AsyncioEngine.has_table(table_name, schema=None)
      :module: sqlalchemy_aio.engine

      Like :meth:`Engine.has_table <sqlalchemy.engine.Engine.has_table>`,
      but is a coroutine.


   .. py:method:: AsyncioEngine.table_names(schema=None, connection=None)
      :module: sqlalchemy_aio.engine

      Like :meth:`Engine.table_names <sqlalchemy.engine.Engine.table_names>`,
      but is a coroutine.


.. py:class:: AsyncioConnection(connection, engine: sqlalchemy_aio.engine.AsyncioEngine)
   :module: sqlalchemy_aio.engine

   Mostly like :class:`sqlalchemy.engine.Connection` except some of the
   methods are coroutines.


   .. py:method:: AsyncioConnection.begin()
      :module: sqlalchemy_aio.engine

      Like :meth:`Connection.begin <sqlalchemy.engine.Connection.begin>`,
      but returns an awaitable that can also be used as an asynchronous
      context manager.

      .. rubric:: Examples

      .. code-block:: python

          async with conn.begin() as trans:
              await conn.execute(...)
              await conn.execute(...)

      .. code-block:: python

          trans = await conn.begin():
          await conn.execute(...)
          await conn.execute(...)
          await trans.commit()


   .. py:method:: AsyncioConnection.begin_nested()
      :module: sqlalchemy_aio.engine

      Like :meth:`Connection.begin_nested        <sqlalchemy.engine.Connection.begin_nested>`, but returns an awaitable
      that can also be used as an asynchronous context manager.

      .. seealso:: :meth:`begin` for examples.


   .. py:method:: AsyncioConnection.close(*args, **kwargs)
      :module: sqlalchemy_aio.engine

      Like :meth:`Connection.close <sqlalchemy.engine.Connection.close>`,
      but is a coroutine.


   .. py:attribute:: AsyncioConnection.closed
      :module: sqlalchemy_aio.engine

      Like the :attr:`Connection.closed        <sqlalchemy.engine.Connection.closed>` attribute.

   .. py:method:: AsyncioConnection.execute(*args, **kwargs)
      :module: sqlalchemy_aio.engine

      Like :meth:`Connection.execute <sqlalchemy.engine.Connection.execute>`,
      but is a coroutine that returns an :class:`AsyncioResultProxy`.

      .. rubric:: Example

      .. code-block:: python

          result = await conn.execute(...)
          data = await result.fetchall()

      .. warning::

          Make sure to explicitly call :meth:`AsyncioResultProxy.close` if the
          :class:`~sqlalchemy.engine.ResultProxy` has pending rows remaining
          otherwise it will be closed during garbage collection. With SQLite,
          this will raise an exception since the DBAPI connection was created
          in a different thread.


   .. py:method:: AsyncioConnection.in_transaction()
      :module: sqlalchemy_aio.engine

      Like the :attr:`Connection.in_transaction        <sqlalchemy.engine.Connection.in_transaction>` attribute.



.. py:class:: AsyncioResultProxy(result_proxy, engine: sqlalchemy_aio.engine.AsyncioEngine)
   :module: sqlalchemy_aio.engine

   Mostly like :class:`sqlalchemy.engine.ResultProxy` except some of the
   methods are coroutines.


   .. py:method:: AsyncioResultProxy.close()
      :module: sqlalchemy_aio.engine

      Like :meth:`ResultProxy.close        <sqlalchemy.engine.ResultProxy.close>`, but is a coroutine.



   .. py:method:: AsyncioResultProxy.fetchall()
      :module: sqlalchemy_aio.engine

      Like :meth:`ResultProxy.fetchall        <sqlalchemy.engine.ResultProxy.fetchall>`, but is a coroutine.



   .. py:method:: AsyncioResultProxy.fetchone()
      :module: sqlalchemy_aio.engine

      Like :meth:`ResultProxy.fetchone        <sqlalchemy.engine.ResultProxy.fetchone>`, but is a coroutine.



   .. py:method:: AsyncioResultProxy.first()
      :module: sqlalchemy_aio.engine

      Like :meth:`ResultProxy.first        <sqlalchemy.engine.ResultProxy.first>`, but is a coroutine.



   .. py:attribute:: AsyncioResultProxy.inserted_primary_key
      :module: sqlalchemy_aio.engine

      Like the :attr:`ResultProxy.inserted_primary_key        <sqlalchemy.engine.ResultProxy.inserted_primary_key>` attribute.

   .. py:method:: AsyncioResultProxy.keys()
      :module: sqlalchemy_aio.engine

      Like :meth:`ResultProxy.keys        <sqlalchemy.engine.ResultProxy.keys>`, but is a coroutine.



   .. py:attribute:: AsyncioResultProxy.returns_rows
      :module: sqlalchemy_aio.engine

      Like the :attr:`ResultProxy.returns_rows        <sqlalchemy.engine.ResultProxy.returns_rows>` attribute.

   .. py:attribute:: AsyncioResultProxy.rowcount
      :module: sqlalchemy_aio.engine

      Like the :attr:`ResultProxy.rowcount        <sqlalchemy.engine.ResultProxy.rowcount>` attribute.

   .. py:method:: AsyncioResultProxy.scalar()
      :module: sqlalchemy_aio.engine

      Like :meth:`ResultProxy.scalar        <sqlalchemy.engine.ResultProxy.scalar>`, but is a coroutine.



.. py:class:: AsyncioTransaction(transaction, engine)
   :module: sqlalchemy_aio.engine

   Mostly like :class:`sqlalchemy.engine.Transaction` except some of the
   methods are coroutines.


   .. py:method:: AsyncioTransaction.close()
      :module: sqlalchemy_aio.engine

      Like :meth:`Transaction.close <sqlalchemy.engine.Transaction.close>`,
      but is a coroutine.


   .. py:method:: AsyncioTransaction.commit()
      :module: sqlalchemy_aio.engine

      Like :meth:`Transaction.commit <sqlalchemy.engine.Transaction.commit>`,
      but is a coroutine.


   .. py:method:: AsyncioTransaction.rollback()
      :module: sqlalchemy_aio.engine

      Like :meth:`Transaction.rollback <sqlalchemy.engine.Transaction.rollback>`,
      but is a coroutine.
