# Changelog

## [0.1.0] - 2025-10-10

### Added
- Initial release of the ETL Watcher SDK
- Pipeline configuration and syncing with `sync_pipeline_config()`
- Execution tracking with `@track_pipeline_execution` decorator
- `WatcherExecutionContext` for parent-child execution chaining
- ETL metrics collection with `ETLMetrics` model
- Support for pipeline watermark management
- Address lineage configuration and syncing
- Comprehensive test suite with pytest
- Documentation with installation and usage examples
- Support for inactive pipeline handling with warnings
- Support for skipping inactive pipeline in `@track_pipeline_execution`
- Connection pooling with `httpx.Client` for better performance
