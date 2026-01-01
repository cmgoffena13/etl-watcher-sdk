Execution Management
====================

This guide will walk through execution management for your pipelines.

Logging Executions
-------------------

You can log executions by using the ``track_pipeline_execution`` decorator.
This will log the execution to the Watcher framework and return the execution id.
This execution id can be used to track the execution and retrieve the metrics.

The ``track_pipeline_execution`` decorator requires the pipeline id and active status as arguments. 
You can also pass in the ``parent_execution_id``, ``watermark``, and ``next_watermark`` as arguments to be logged.

Exception Handling
~~~~~~~~~~~~~~~~~~

The decorator handles exceptions automatically:

- **Unexpected exceptions** are automatically caught, logged as failures in the Watcher API, and then re-raised
- **Set `completed_successfully=False`** for business logic failures (not exceptions)

.. warning::
   Do not catch exceptions and return `ETLResult`. This silences the error, make sure to 
   raise the exception and the decorator will automatically mark the execution as failed.

Example Usage
~~~~~~~~~~~~~

.. code-block:: python

    from watcher import Watcher, WatcherContext

    watcher = Watcher("https://api.watcher.example.com")

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def etl_pipeline():
        try:
            # Your ETL logic here
            if some_condition_fails:
                return ETLResult(completed_successfully=False, execution_metadata={"error": "Data quality issues"})
            return ETLResult(completed_successfully=True, inserts=100, total_rows=100)
        except Exception as e:
            # Don't catch exceptions - let them bubble up to the decorator
            # The decorator will automatically mark the execution as failed
            raise e

    # Access results
    result = etl_pipeline()

.. code-block:: python

    from watcher import Watcher, WatcherContext

    watcher = Watcher("https://api.watcher.example.com")

    synced_config = watcher.sync_pipeline_config(MY_ETL_PIPELINE_CONFIG)

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline():


        # Work here

        return ETLResult(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
        )

    my_pipeline()

Custom ETL Results
------------------

You can extend ``ETLResult`` with custom fields to return additional data from your pipeline:

.. code-block:: python

    from pydantic import BaseModel
    from watcher import ETLResult

    class CustomETLResult(ETLResult):
        data_quality_score: Optional[float] = None

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline():

        # ... do work ...
        
        return CustomETLResult(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
            data_quality_score=0.95
        )

    # Access custom fields
    output = my_pipeline()
    print(f"Quality score: {output.result.data_quality_score}")

.. note::
   Custom fields are only accessible in your application code. Only the standard ETLResult fields 
   (completed_successfully, inserts, updates, etc.) are sent to the Watcher API.

ETL Results
------------

The ETLResult is a class that is required to be returned from your pipeline function 
if using the ``track_pipeline_execution`` decorator.
It contains the metrics for your pipeline that are logged to the Watcher framework.

.. code-block:: python

    class ETLResult(BaseModel):
        completed_successfully: bool
        inserts: Optional[int] = Field(default=None, ge=0)
        updates: Optional[int] = Field(default=None, ge=0)
        soft_deletes: Optional[int] = Field(default=None, ge=0)
        total_rows: Optional[int] = Field(default=None, ge=0)
        execution_metadata: Optional[dict] = None

Code Example:

.. code-block:: python

    from watcher import ETLResult

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline():


        # Work here

        return ETLResult(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
        )

Execution Results
-----------------

The ExecutionResults is a class that is returned from your pipeline function. This 
wraps around the ETLResult class and adds the execution id. This is to ensure access 
to the execution id for any usage. 

.. code-block:: python

    from watcher import ExecutionResult

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline() -> ExecutionResult:

        # Work here

        return ETLResult(
                completed_successfully=True,
                inserts=100,
                total_rows=100,
            )

    output = my_pipeline()
    print(output.execution_id)
    print(output.result)
    print(output.result.inserts)

Hierarchical Executions
------------------------

For parent-child execution relationships, you have two options:

**Option 1: track_child_pipeline_execution() method (Recommended)**

.. code-block:: python

    from etl_watcher_sdk import Watcher, ETLResult, WatcherContext

    watcher = Watcher(api_key="your-api-key", base_url="https://api.example.com")

    def process_ticker_data(ticker: str, watcher_context: WatcherContext) -> ETLResult:
        # Child function that processes individual ticker data
        print(f"Processing {ticker} with watermark: {watcher_context.watermark}")
        
        return ETLResult(
            completed_successfully=True,
            total_rows=100,
            inserts=100,
            execution_metadata={"ticker": ticker, "batch_id": "123"}
        )

    @watcher.track_pipeline_execution(pipeline_id=123)
    def main_etl_pipeline(watcher_context: WatcherContext) -> ETLResult:
        tickers = ["AAPL", "GOOGL", "MSFT"]
        total_processed = 0
        
        for ticker in tickers:
            # One line - calls function and tracks as child execution
            child_result = watcher.track_child_pipeline_execution(
                pipeline_id=456,
                active=True,
                parent_execution_id=watcher_context.execution_id,
                func=process_ticker_data,
                ticker=ticker,
                watermark=watcher_context.watermark,
                next_watermark=watcher_context.next_watermark
            )
            
            total_processed += child_result.result.total_rows
            print(f"Child execution {child_result.execution_id} processed {child_result.result.total_rows} rows")
        
        return ETLResult(completed_successfully=True, total_rows=total_processed)

.. note::
    The function that is called by ``track_child_pipeline_execution`` 
    must return an ``ETLResult`` or a model that inherits from ``ETLResult``. 
    It also must not be decorated with ``track_pipeline_execution``.

**Option 2: Nested decorators (for small functions)**

.. code-block:: python

    @watcher.track_pipeline_execution(pipeline_id=parent_pipeline_id, active=True)
    def parent_pipeline(watcher_context: WatcherContext):
        # Parent logic here
        
        @watcher.track_pipeline_execution(
            pipeline_id=child_pipeline_id, 
            active=True,
            parent_execution_id=watcher_context.execution_id
        )
        def child_pipeline():
            # Child logic here
            return ETLResult(completed_successfully=True, total_rows=100)
        
        child_pipeline()  # Call the child
        return ETLResult(completed_successfully=True, total_rows=200)

**Method Parameters (Option 1):**

- ``pipeline_id`` (int) - ID of the child pipeline (from child config)
- ``active`` (bool) - Whether the pipeline is active (from child config)
- ``parent_execution_id`` (int) - ID of the parent execution (from watcher_context)
- ``func`` (callable) - Function to execute as child execution
- ``*args, **kwargs`` - Arguments to pass to the function
- ``watermark`` (optional) - Watermark to pass to the child execution (from child config)
- ``next_watermark`` (optional) - Next watermark to pass to the child execution (from child config)

**Key Features:**

- **Automatic WatcherContext injection** - If your function has a `watcher_context` parameter, it gets injected automatically
- **Full ETLResult logging** - Captures and logs all metrics (inserts, updates, total_rows, etc.)
- **Error handling** - Automatically marks as failed if exception occurs
- **Watermark support** - Child functions can access watermarks via `watcher_context`

Watcher Execution Context
-----------------

The WatcherContext is a class that is passed to your pipeline function.
It contains the execution id, pipeline id, watermark, and next watermark variables. 
Your function must have `watcher_context` as a parameter if using the WatcherContext.

.. code-block:: python

    from watcher import WatcherContext

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline(watcher_context: WatcherContext):

        # Work here

        print(watcher_context.execution_id)
        print(watcher_context.pipeline_id)
        print(watcher_context.watermark)
        print(watcher_context.next_watermark)

        return ETLResult(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
        )
        

Active Flag
-----------

You can set a Pipeline's active flag to False to skip the execution. This is normally triggered 
through the Watcher framework directly as the active flag is received from the Watcher API.

.. code-block:: python

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline(watcher_context: WatcherContext):

        # Function IS SKIPPED if active is False

        return ETLResult(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
        )

    my_pipeline()

.. note::
    This can be a useful functionality to use in your pipelines to skip executions if needed.

Manual Execution Management
----------------------------

For advanced use cases, especially when integrating with orchestration frameworks like Airflow or Dagster, you can manually manage execution lifecycle using the following methods:

**start_pipeline_execution()**

Starts a new pipeline execution and returns the execution ID. This is useful when you need to start an execution without using the decorator pattern.

.. code-block:: python

    from watcher import Watcher
    import pendulum

    watcher = Watcher("https://api.watcher.example.com")

    # Start execution with minimal parameters
    execution_id = watcher.start_pipeline_execution(pipeline_id=123)

    # Start execution with all parameters
    execution_id = watcher.start_pipeline_execution(
        pipeline_id=123,
        start_date=pendulum.now(),
        watermark="2024-01-01",  # Associated with run, only metadata
        next_watermark="2024-01-02",  # Associated with run, only metadata
        parent_execution_id=456
    )

**Parameters:**

- ``pipeline_id`` (int, required) - The ID of the pipeline to execute
- ``start_date`` (DateTime, optional) - Start date for the execution
- ``watermark`` (str | int | DateTime | Date, optional) - Watermark value for the execution
- ``next_watermark`` (str | int | DateTime | Date, optional) - Next watermark value
- ``parent_execution_id`` (int, optional) - ID of the parent execution for hierarchical tracking

**Returns:**

- ``int`` - The execution ID of the started execution

**end_pipeline_execution()**

Ends a pipeline execution with the provided metrics and status. This is useful when you need to manually end an execution that was started with ``start_pipeline_execution()``.

.. code-block:: python

    from watcher import Watcher
    import pendulum

    watcher = Watcher("https://api.watcher.example.com")

    # End execution with minimal parameters
    watcher.end_pipeline_execution(
        execution_id=789,
        completed_successfully=True
    )

    # End execution with all metrics
    watcher.end_pipeline_execution(
        execution_id=789,
        completed_successfully=True,
        end_date=pendulum.now(),
        inserts=100,
        updates=50,
        soft_deletes=10,
        total_rows=1000,
        execution_metadata={"source": "database", "batch_id": "123"}
    )

    # Mark execution as failed
    watcher.end_pipeline_execution(
        execution_id=789,
        completed_successfully=False,
        execution_metadata={"error": "Data quality check failed"}
    )

**Parameters:**

- ``execution_id`` (int, required) - The ID of the execution to end
- ``completed_successfully`` (bool, required) - Whether the execution completed successfully
- ``end_date`` (DateTime, optional) - End date for the execution
- ``inserts`` (int, optional) - Number of rows inserted
- ``updates`` (int, optional) - Number of rows updated
- ``soft_deletes`` (int, optional) - Number of rows soft deleted
- ``total_rows`` (int, optional) - Total number of rows processed
- ``execution_metadata`` (dict, optional) - Additional metadata for the execution

**update_pipeline_next_watermark()**

Updates the next watermark for a pipeline. This is useful for manually updating watermarks outside of the normal execution flow.

.. code-block:: python

    from watcher import Watcher
    import pendulum

    watcher = Watcher("https://api.watcher.example.com")

    # Update with string watermark
    watcher.update_pipeline_next_watermark(
        pipeline_id=123,
        next_watermark="2024-01-02"
    )

    # Update with integer watermark
    watcher.update_pipeline_next_watermark(
        pipeline_id=123,
        next_watermark=20240102
    )

    # Update with DateTime watermark
    watcher.update_pipeline_next_watermark(
        pipeline_id=123,
        next_watermark="2024-01-02T10:00:00"
    )

**Parameters:**

- ``pipeline_id`` (int, required) - The ID of the pipeline to update
- ``next_watermark`` (str | int | DateTime | Date, required) - The new next watermark value

**Use Cases:**

These manual methods are particularly useful for:

- **Orchestration Framework Integration**: When integrating with Airflow, Dagster, or other orchestration tools where you need fine-grained control over execution lifecycle
- **Parent-Child Execution Tracking**: When managing parent executions that span multiple child tasks
- **Custom Error Handling**: When you need custom error handling logic before completing an execution
- **Watermark Management**: When you need to update watermarks after a pipeline runs rather than before