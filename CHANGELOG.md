# Changelog

Sections: Added, Changed, Deprecated, Removed, Fixed, Security

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

## [0.1.1] - 2025-10-10

### Added
 - Simplified `SourceAddress` and `TargetAddress` into `Address`
 - Simplified imports so `from watcher import *` can work

## [0.1.16] - 2025-10-11

### Changed
- `ETLMetrics` is now `ETLResult`
 - Added `completed_successfully` to `ETLResult` to account for error handling
 - Restructured `SyncedPipelineConfig` to be more standardized
 - Added more fields for `Address`

## [0.1.18] - 2025-10-11

### Added
- `WatcherAPIError` and `WatcherNetworkError` custom exceptions with detailed API context
- HTTP retry logic with exponential backoff and jitter to prevent thundering herd
- `retry_http` decorator for custom retry behavior on HTTP calls
- Better error handling that surfaces API error details (status codes, error codes, response text)
- Centralized test fixtures in `conftest.py` for better test organization

## [0.1.19] - 2025-10-11

### Added
- `trigger_timeliness_check(lookback_minutes)` method for triggering timeliness monitoring
- `trigger_freshness_check()` method for triggering freshness monitoring  
- `trigger_celery_queue_check()` method for monitoring Celery queue health

## [0.1.2] - 2025-10-11

### Changed
- Renamed `ETLResults` to be singular `ETLResult`

## [0.1.21] - 2025-10-11

### Changed
- Renamed `ExecutionResult.results` field to `ExecutionResult.result` for consistency
- Made `AddressLineage` Optional in the `PipelineConfig` class

## [0.1.22] - 2025-10-11

### Changed
- Renamed `WatcherExecutionContext` to `WatcherContext` for simplicity

## [0.1.23] - 2025-10-11

### Added
- Added `track_child_pipeline_execution` method to better handle hierachical execution

## [0.1.24] - 2025-10-19

### Added
- Added `address_metadata` to PipelineConfig

## [0.1.3] - 2025-10-25

### Added
- Added `OrchestratedETL` class for Dagster and Airflow integration
- Added `OrchestrationContext` for framework-specific metadata detection
- Added parent execution tracking with `start_parent_execution` and `end_parent_execution` methods
- Added orchestration context injection into ETL metadata
- Added comprehensive documentation for orchestration integration

## [0.1.31] - 2025-10-25

### Upgraded Packages

## [0.1.41] - 2025-11-1

### Upgraded Packages

### Added
- New ProductionHTTPClient to have better http calls and retries

## [0.1.42] - 2026-01-01

### Added
 - `start_process_execution` , `end_process_execution` , and `update_pipeline_next_watermark` methods to client