# Change Log
## [Unreleased][unreleased]
N/A

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

[unreleased]: https://github.com/RazerM/sqlalchemy_aio/compare/0.12.0...HEAD
[0.12.0]: https://github.com/RazerM/sqlalchemy_aio/compare/0.11.0...0.12.0
[0.11.0]: https://github.com/RazerM/sqlalchemy_aio/compare/0.10.0...0.11.0
[0.10.0]: https://github.com/RazerM/sqlalchemy_aio/compare/458d37d8...0.10.0
