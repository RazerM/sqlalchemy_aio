class AlreadyQuit(Exception):
    """Raised by :class:`~sqlalchemy_aio.base.ThreadWorker` if an attempt is
    made to use it after its thread has quit.
    """


class BlockingWarning(RuntimeWarning):
    """Emitted when an :class:`~sqlalchemy_aio.base.AsyncEngine` or
    :class:`~sqlalchemy_aio.base.AsyncConnection` is used in a blocking
    fashion accidentally.

    For example, it is emitted in this case:

    .. code-block:: python

        engine = create_engine(..., strategy=TRIO_STRATEGY)
        Table(..., autoload_with=engine)
    """
