Core Models
===========

ETLResult
---------

The primary model for ETL execution results. Return this from your decorated ETL functions.

.. code-block:: python

    class ETLResult(BaseModel):
        completed_successfully: bool
        inserts: Optional[int] = Field(default=None, ge=0)
        updates: Optional[int] = Field(default=None, ge=0)
        soft_deletes: Optional[int] = Field(default=None, ge=0)
        total_rows: Optional[int] = Field(default=None, ge=0)
        execution_metadata: Optional[dict] = None

**Usage:**

.. code-block:: python

    @watcher.track_pipeline_execution(pipeline_id=123)
    def my_etl_pipeline(watcher_context: WatcherExecutionContext):
        # Your ETL logic here
        return ETLResult(
            completed_successfully=True,
            inserts=100,
            total_rows=1000,
            execution_metadata={"partition": "2025-01-01"}
        )

**Custom ETL Results:**
You can extend ``ETLResult`` for custom data:

.. code-block:: python

    class CustomETLResult(ETLResult):
        custom_metric: Optional[float] = None

WatcherExecutionContext
-----------------------

Context object injected into decorated ETL functions.

.. code-block:: python

    class WatcherExecutionContext(BaseModel):
        execution_id: int
        pipeline_id: int
        watermark: Optional[Union[str, int, DateTime, Date]] = None
        next_watermark: Optional[Union[str, int, DateTime, Date]] = None

**Usage:**

.. code-block:: python

    @watcher.track_pipeline_execution(pipeline_id=123)
    def my_etl_pipeline(watcher_context: WatcherExecutionContext):
        print(f"Execution ID: {watcher_context.execution_id}")
        print(f"Pipeline ID: {watcher_context.pipeline_id}")
        # Use watermark for incremental processing
        if watcher_context.watermark:
            process_from_watermark(watcher_context.watermark)

ExecutionResult
---------------

Returned by the ``track_pipeline_execution`` decorator.

.. code-block:: python

    class ExecutionResult(BaseModel):
        execution_id: int
        result: ETLResult

Pipeline Models
===============

Pipeline
--------

Core pipeline definition. This information is synced with the Watcher Framework.

.. code-block:: python

    class Pipeline(BaseModel):
        name: str = Field(max_length=150, min_length=1)
        pipeline_type_name: str = Field(max_length=150, min_length=1)
        pipeline_metadata: Optional[dict] = None
        freshness_number: Optional[int] = Field(default=None, gt=0)
        freshness_datepart: Optional[DatePartEnum] = None
        timeliness_number: Optional[int] = Field(default=None, gt=0)
        timeliness_datepart: Optional[DatePartEnum] = None

PipelineConfig
--------------

Complete pipeline configuration including address lineage and watermarks.

.. code-block:: python

    class PipelineConfig(BaseModel):
        pipeline: Pipeline
        address_lineage: Optional[AddressLineage] = None
        default_watermark: Optional[Union[str, int, DateTime, Date]] = None
        next_watermark: Optional[Union[str, int, DateTime, Date]] = None

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

Pipeline configuration after syncing with the Watcher API.

.. code-block:: python

    class SyncedPipelineConfig(PipelineConfig):
        pipeline: _PipelineWithResponse  # Includes id and active fields
        watermark: Optional[Union[str, int, DateTime, Date]] = None

**Usage:**

.. code-block:: python

    synced_config = watcher.sync_pipeline_config(config)
    print(f"Pipeline ID: {synced_config.pipeline.id}")
    print(f"Active: {synced_config.pipeline.active}")
    print(f"Watermark: {synced_config.watermark}")

Address Models
==============

Address
-------

Unified address model for both source and target addresses.

.. code-block:: python

    class Address(BaseModel):
        name: str = Field(max_length=150, min_length=1)
        address_type_name: str = Field(max_length=150, min_length=1)
        address_type_group_name: str = Field(max_length=150, min_length=1)
        database_name: Optional[str] = Field(None, max_length=50)
        schema_name: Optional[str] = Field(None, max_length=50)
        table_name: Optional[str] = Field(None, max_length=50)
        primary_key: Optional[str] = Field(None, max_length=50)

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

Defines the data lineage between source and target addresses. This information is synced with the Watcher Framework.

.. code-block:: python

    class AddressLineage(BaseModel):
        source_addresses: List[Address]
        target_addresses: List[Address]

**Usage:**

.. code-block:: python

    lineage = AddressLineage(
        source_addresses=[source_address],
        target_addresses=[target_address]
    )

Exception Models
================

WatcherAPIError
---------------

Raised for API-related errors with detailed context.

.. code-block:: python

    class WatcherAPIError(WatcherError):
        status_code: Optional[int] = None
        response_text: Optional[str] = None
        response_headers: Optional[Dict[str, str]] = None
        error_code: Optional[str] = None
        error_details: Optional[Dict[str, Any]] = None

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

.. code-block:: python

    class WatcherNetworkError(WatcherError):
        pass

**Usage:**

.. code-block:: python

    try:
        watcher.sync_pipeline_config(config)
    except WatcherNetworkError as e:
        print(f"Network Error: {e}")
        # Handle network issues