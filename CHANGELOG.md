# Change Log
## [Unreleased][unreleased]

### Added
- Python 3.9 and 3.10 support.

### Removed
- The previously deprecated loop argument to `AsyncioEngine`.

### Fixed
- Added `sqlalchemy<1.4` version constraint since SQLAlchemy 1.4 is not supported.

## [0.16.0]

### Changed
- Trio support requires trio 0.15+

### Deprecated
- The loop argument to `AsyncioEngine`.

### Removed
- Support for Python 3.5

## [0.15.0]
### Fixed
- Concurrency problems in `AsyncioThreadWorker` ([#20][]).
- Wait for worker to quit if `AsyncConnection.connect` fails.

### Changed
- Trio support requires trio 0.12+

[#20]: https://github.com/RazerM/sqlalchemy_aio/issues/20

## [0.14.1]
### Fixed
- Wait for worker to quit if `AsyncEngine.connect` fails ([#18][]).

[#18]: https://github.com/RazerM/sqlalchemy_aio/issues/18

## [0.14.0]
### Added
- `AsyncConnection.dialect` property.
- `AsyncEngine.sync_engine` property.
- `AsyncConnection.sync_connection`property.
- Blocking method `run_callable` has been implemented for
  `AsyncConnection` and `AsyncEngine`. This allows
  `Table(..., autoload_with=engine)`, which emits a `BlockingWarning` ([#10][]).
- Detects attempts to use `Table().create(bind=engine)` or
  `MetaData().create_all()` and raises a helpful error message.
- Detects attempts to use `MetData().reflect()` and raises a helpful
  error message ([#13][]).
- `AsyncConnection.connect()` method.
- Public `run_in_thread()` async method has been added to `AsyncConnection`
  and `AsyncEngine`.
- Detects attempts to use `event.listen()` with `AsyncConnection` or
  `AsyncEngine` and raises a more helpful error message ([#1][]).
  
### Changed
- Trio support requires trio 0.9+

### Fixed
- `ThreadWorker.quit()` will raise `AlreadyQuit` instead of blocking.
  This is only called internally.
- Connections created using `AsyncEngine.begin()` now create their own
  worker, like `AsyncEngine.connect()`.
- Passing `echo=True` to `create_engine` was broken ([#12][]).

[#1]: https://github.com/RazerM/sqlalchemy_aio/issues/1
[#10]: https://github.com/RazerM/sqlalchemy_aio/issues/10
[#12]: https://github.com/RazerM/sqlalchemy_aio/issues/12
[#13]: https://github.com/RazerM/sqlalchemy_aio/issues/13

## [0.13.0]
### Added
- [Trio] support with `TRIO_STRATEGY`.

### Changed
- A new `ThreadWorker` class is used internally to defer work to instead
  of using a `ThreadPoolExecutor`.

[Trio]: https://github.com/python-trio/trio

## [0.12.0] - 2018-02-06
### Added
- `AsyncioResultProxy.fetchmany`
- `AsyncioResultProxy.__aiter__`

## [0.11.0] - 2017-03-12
### Added
- `AsyncioEngine.scalar()`
- `AsyncioConnection.scalar()`

### Fixed
- Connections now get their own thread. Now threadsafe DBAPI modules are more
  useful without passing a custom executor as in 0.10.0

### Changed
- **Backwards incompatible:** removed `executor` argument, since the engine
  takes care of threads now.


## [0.10.0] - 2016-12-19
Initial release.

[unreleased]: https://github.com/RazerM/sqlalchemy_aio/compare/0.16.0...HEAD
[0.16.0]: https://github.com/RazerM/sqlalchemy_aio/compare/0.15.0...0.16.0
[0.15.0]: https://github.com/RazerM/sqlalchemy_aio/compare/0.14.1...0.15.0
[0.14.1]: https://github.com/RazerM/sqlalchemy_aio/compare/0.14.0...0.14.1
[0.14.0]: https://github.com/RazerM/sqlalchemy_aio/compare/0.13.0...0.14.0
[0.13.0]: https://github.com/RazerM/sqlalchemy_aio/compare/0.12.0...0.13.0
[0.12.0]: https://github.com/RazerM/sqlalchemy_aio/compare/0.11.0...0.12.0
[0.11.0]: https://github.com/RazerM/sqlalchemy_aio/compare/0.10.0...0.11.0
[0.10.0]: https://github.com/RazerM/sqlalchemy_aio/compare/458d37d8...0.10.0
