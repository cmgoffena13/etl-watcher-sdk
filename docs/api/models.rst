Core Models
===========

ETLResult
---------

Return this from your decorated ETL functions to report execution results.

**Available Fields:**

- ``completed_successfully`` (bool) - Whether the ETL completed successfully
- ``inserts`` (int, optional) - Number of records inserted
- ``updates`` (int, optional) - Number of records updated  
- ``soft_deletes`` (int, optional) - Number of records soft deleted
- ``total_rows`` (int, optional) - Total number of rows processed
- ``execution_metadata`` (dict, optional) - Custom metadata about the execution

**Usage:**

.. code-block:: python

    @watcher.track_pipeline_execution(pipeline_id=123)
    def my_etl_pipeline(watcher_context: WatcherContext):
        # Your ETL logic here
        return ETLResult(
            completed_successfully=True,
            inserts=100,
            total_rows=1000,
            execution_metadata={"partition": "2025-01-01"}
        )

**Custom Fields:**
You can add custom fields by extending ``ETLResult``:

.. code-block:: python

    class CustomETLResult(ETLResult):
        custom_metric: Optional[float] = None
        processing_time: Optional[float] = None

WatcherContext
-----------------------

Context object automatically injected into your decorated ETL functions.

**Available Fields:**

- ``execution_id`` (int) - Unique ID for this execution
- ``pipeline_id`` (int) - ID of the pipeline being executed
- ``watermark`` (str/int/DateTime/Date, optional) - Current watermark for incremental processing
- ``next_watermark`` (str/int/DateTime/Date, optional) - Next watermark to set after execution

**Usage:**

.. code-block:: python

    @watcher.track_pipeline_execution(pipeline_id=123)
    def my_etl_pipeline(watcher_context: WatcherContext):
        print(f"Execution ID: {watcher_context.execution_id}")
        print(f"Pipeline ID: {watcher_context.pipeline_id}")
        # Use watermark for incremental processing
        if watcher_context.watermark:
            process_from_watermark(watcher_context.watermark)

ExecutionResult
---------------

Returned by the ``track_pipeline_execution`` decorator.

**Available Fields:**

- ``execution_id`` (int) - Unique ID for this execution
- ``result`` (ETLResult) - The ETL results from your function:

  - ``result.completed_successfully`` (bool) - Whether the ETL completed successfully
  - ``result.inserts`` (int, optional) - Number of records inserted
  - ``result.updates`` (int, optional) - Number of records updated
  - ``result.soft_deletes`` (int, optional) - Number of records soft deleted
  - ``result.total_rows`` (int, optional) - Total number of rows processed
  - ``result.execution_metadata`` (dict, optional) - Custom metadata about the execution

**Usage:**

.. code-block:: python

    result = my_pipeline()
    print(f"Execution ID: {result.execution_id}")
    print(f"Success: {result.result.completed_successfully}")
    print(f"Rows processed: {result.result.total_rows}")

Pipeline Configuration
======================

Pipeline
--------

Core pipeline definition that gets synced with the Watcher Framework.

**Available Fields:**

- ``name`` (str) - Pipeline name (1-150 characters)
- ``pipeline_type_name`` (str) - Type of pipeline (1-150 characters)
- ``pipeline_metadata`` (dict, optional) - Custom metadata about the pipeline
- ``freshness_number`` (int, optional) - Number for freshness monitoring
- ``freshness_datepart`` (DatePartEnum, optional) - Date part for freshness monitoring
- ``timeliness_number`` (int, optional) - Number for timeliness monitoring  
- ``timeliness_datepart`` (DatePartEnum, optional) - Date part for timeliness monitoring

PipelineConfig
--------------

Complete pipeline configuration including address lineage and watermarks.

**Available Fields:**

- ``pipeline`` - The pipeline definition:

  - ``pipeline.name`` (str) - Pipeline name (1-150 characters)
  - ``pipeline.pipeline_type_name`` (str) - Type of pipeline (1-150 characters)
  - ``pipeline.pipeline_metadata`` (dict, optional) - Custom metadata about the pipeline
  - ``pipeline.freshness_number`` (int, optional) - Number for freshness monitoring
  - ``pipeline.freshness_datepart`` (DatePartEnum, optional) - Date part for freshness monitoring
  - ``pipeline.timeliness_number`` (int, optional) - Number for timeliness monitoring
  - ``pipeline.timeliness_datepart`` (DatePartEnum, optional) - Date part for timeliness monitoring

- ``address_lineage`` (AddressLineage, optional) - Data lineage information:
  - ``address_lineage.source_addresses`` (List[Address]) - List of source addresses
  - ``address_lineage.target_addresses`` (List[Address]) - List of target addresses

  - Each Address contains:

    - ``name`` (str) - Address name (1-150 characters)
    - ``address_type_name`` (str) - Type of address (1-150 characters)
    - ``address_type_group_name`` (str) - Group name (1-150 characters)
    - ``database_name`` (str, optional) - Database name (max 50 characters)
    - ``schema_name`` (str, optional) - Schema name (max 50 characters)
    - ``table_name`` (str, optional) - Table name (max 50 characters)
    - ``primary_key`` (str, optional) - Primary key field (max 50 characters)

- ``default_watermark`` (str/int/DateTime/Date, optional) - Default watermark for the pipeline
- ``next_watermark`` (str/int/DateTime/Date, optional) - Next watermark to set

**Usage:**

.. code-block:: python

    config = PipelineConfig(
        pipeline=Pipeline(
            name="my-etl-pipeline",
            pipeline_type_name="data-transformation",
            pipeline_metadata={"version": "1.0"}
        ),
        address_lineage=AddressLineage(
            source_addresses=[source_address],
            target_addresses=[target_address]
        ),
        default_watermark="2025-01-01",
        next_watermark="2025-01-02"
    )

SyncedPipelineConfig
--------------------

Pipeline configuration after syncing with the Watcher API. **Extends PipelineConfig** with additional fields from the API response.

**Available Fields:**

- ``pipeline`` - The pipeline definition with additional fields:

  - ``pipeline.name`` (str) - Pipeline name (1-150 characters)
  - ``pipeline.pipeline_type_name`` (str) - Type of pipeline (1-150 characters)
  - ``pipeline.pipeline_metadata`` (dict, optional) - Custom metadata about the pipeline
  - ``pipeline.freshness_number`` (int, optional) - Number for freshness monitoring
  - ``pipeline.freshness_datepart`` (DatePartEnum, optional) - Date part for freshness monitoring
  - ``pipeline.timeliness_number`` (int, optional) - Number for timeliness monitoring
  - ``pipeline.timeliness_datepart`` (DatePartEnum, optional) - Date part for timeliness monitoring
  - ``pipeline.id`` (int) - Pipeline ID assigned by the API
  - ``pipeline.active`` (bool) - Whether the pipeline is active

- ``address_lineage`` (AddressLineage, optional) - Data lineage information:

  - ``address_lineage.source_addresses`` (List[Address]) - List of source addresses
  - ``address_lineage.target_addresses`` (List[Address]) - List of target addresses

  - Each Address contains:

    - ``name`` (str) - Address name (1-150 characters)
    - ``address_type_name`` (str) - Type of address (1-150 characters)
    - ``address_type_group_name`` (str) - Group name (1-150 characters)
    - ``database_name`` (str, optional) - Database name (max 50 characters)
    - ``schema_name`` (str, optional) - Schema name (max 50 characters)
    - ``table_name`` (str, optional) - Table name (max 50 characters)
    - ``primary_key`` (str, optional) - Primary key field (max 50 characters)
- ``default_watermark`` (str/int/DateTime/Date, optional) - Default watermark for the pipeline

- ``next_watermark`` (str/int/DateTime/Date, optional) - Next watermark to set
- ``watermark`` (str/int/DateTime/Date, optional) - Current watermark from the API

**Usage:**

.. code-block:: python

    synced_config = watcher.sync_pipeline_config(config)
    print(f"Pipeline ID: {synced_config.pipeline.id}")
    print(f"Active: {synced_config.pipeline.active}")
    print(f"Watermark: {synced_config.watermark}")

Address Lineage
============

Address
-------

Represents a data source or target for lineage tracking.

**Available Fields:**

- ``name`` (str) - Address name (1-150 characters)
- ``address_type_name`` (str) - Type of address (1-150 characters)
- ``address_type_group_name`` (str) - Group name (1-150 characters)
- ``database_name`` (str, optional) - Database name (max 50 characters)
- ``schema_name`` (str, optional) - Schema name (max 50 characters)
- ``table_name`` (str, optional) - Table name (max 50 characters)
- ``primary_key`` (str, optional) - Primary key field (max 50 characters)

**Usage:**

.. code-block:: python

    source_address = Address(
        name="source_db.source_schema.users",
        address_type_name="postgres",
        address_type_group_name="database",
        database_name="source_db",
        schema_name="public",
        table_name="users",
        primary_key="user_id"
    )

AddressLineage
--------------

Defines the data lineage between source and target addresses.

**Available Fields:**

- ``source_addresses`` (List[Address]) - List of source addresses:
  - Each Address contains:
    - ``name`` (str) - Address name (1-150 characters)
    - ``address_type_name`` (str) - Type of address (1-150 characters)
    - ``address_type_group_name`` (str) - Group name (1-150 characters)
    - ``database_name`` (str, optional) - Database name (max 50 characters)
    - ``schema_name`` (str, optional) - Schema name (max 50 characters)
    - ``table_name`` (str, optional) - Table name (max 50 characters)
    - ``primary_key`` (str, optional) - Primary key field (max 50 characters)
- ``target_addresses`` (List[Address]) - List of target addresses:
  - Each Address contains:
    - ``name`` (str) - Address name (1-150 characters)
    - ``address_type_name`` (str) - Type of address (1-150 characters)
    - ``address_type_group_name`` (str) - Group name (1-150 characters)
    - ``database_name`` (str, optional) - Database name (max 50 characters)
    - ``schema_name`` (str, optional) - Schema name (max 50 characters)
    - ``table_name`` (str, optional) - Table name (max 50 characters)
    - ``primary_key`` (str, optional) - Primary key field (max 50 characters)

**Usage:**

.. code-block:: python

    lineage = AddressLineage(
        source_addresses=[source_address],
        target_addresses=[target_address]
    )

Error Handling
===============

WatcherAPIError
---------------

Raised for API-related errors with detailed context.

**Available Fields:**

- ``status_code`` (int, optional) - HTTP status code
- ``response_text`` (str, optional) - Response text from the API
- ``response_headers`` (dict, optional) - Response headers
- ``error_code`` (str, optional) - Specific error code from the API
- ``error_details`` (dict, optional) - Additional error details

**Usage:**

.. code-block:: python

    try:
        watcher.sync_pipeline_config(config)
    except WatcherAPIError as e:
        print(f"API Error: {e}")
        print(f"Status: {e.status_code}")
        print(f"Error Code: {e.error_code}")

WatcherNetworkError
-------------------

Raised for network/connection errors.

**Usage:**

.. code-block:: python

    try:
        watcher.sync_pipeline_config(config)
    except WatcherNetworkError as e:
        print(f"Network Error: {e}")
        # Handle network issues