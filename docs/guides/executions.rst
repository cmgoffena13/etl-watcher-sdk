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

- **Unexpected exceptions** (not handled by your code) are automatically logged as failures in the Watcher API
- **Set `completed_successfully=False`** for any errors you handle internally

Example Usage
~~~~~~~~~~~~~

.. code-block:: python

    from watcher import Watcher, WatcherExecutionContext

    watcher = Watcher("https://api.watcher.example.com")

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def etl_pipeline():
        try:
            # Your ETL logic here
            if some_condition_fails:
                return ETLResults(completed_successfully=False, execution_metadata={"error": "Data quality issues"})
            return ETLResults(completed_successfully=True, inserts=100, total_rows=100)
        except Exception as e:
            return ETLResults(completed_successfully=False, execution_metadata={"exception": str(e)})

    # Access results
    result = etl_pipeline()

.. code-block:: python

    from watcher import Watcher, WatcherExecutionContext

    watcher = Watcher("https://api.watcher.example.com")

    synced_config = watcher.sync_pipeline_config(MY_ETL_PIPELINE_CONFIG)

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline():


        # Work here

        return ETLResults(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
        )

    my_pipeline()

Custom ETL Results
------------------

You can extend ``ETLResults`` with custom fields to return additional data from your pipeline:

.. code-block:: python

    from pydantic import BaseModel
    from watcher import ETLResults

    class CustomETLResults(ETLResults):
        data_quality_score: Optional[float] = None

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline():

        # ... do work ...
        
        return CustomETLResults(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
            data_quality_score=0.95
        )

    # Access custom fields
    output = my_pipeline()
    print(f"Quality score: {output.results.data_quality_score}")

.. note::
   Custom fields are only accessible in your application code. Only the standard ETLResults fields 
   (completed_successfully, inserts, updates, etc.) are sent to the Watcher API.

ETL Results
------------

The ETLResults is a class that is required to be returned from your pipeline function 
if using the ``track_pipeline_execution`` decorator.
It contains the metrics for your pipeline that are logged to the Watcher framework.

.. code-block:: python

    class ETLResults(BaseModel):
        completed_successfully: bool
        inserts: Optional[int] = Field(default=None, ge=0)
        updates: Optional[int] = Field(default=None, ge=0)
        soft_deletes: Optional[int] = Field(default=None, ge=0)
        total_rows: Optional[int] = Field(default=None, ge=0)
        execution_metadata: Optional[dict] = None

Code Example:

.. code-block:: python

    from watcher import ETLResults

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline():


        # Work here

        return ETLResults(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
        )

Execution Results
-----------------

The ExecutionResults is a class that is returned from your pipeline function. This 
wraps around the ETLResults class and adds the execution id. This is to ensure access 
to the execution id for any usage. 

.. code-block:: python

    from watcher import ExecutionResult

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline() -> ExecutionResult:

        # Work here

        return ETLResults(
                completed_successfully=True,
                inserts=100,
                total_rows=100,
            )

    output = my_pipeline()
    print(output.execution_id)
    print(output.results)
    print(output.results.inserts)

Watcher Execution Context
-----------------

The WatcherExecutionContext is a class that is passed to your pipeline function.
It contains the execution id, pipeline id, watermark, and next watermark variables. 
Your function must have `watcher_context` as a parameter if using the WatcherExecutionContext.

.. code-block:: python

    from watcher import WatcherExecutionContext

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline(watcher_context: WatcherExecutionContext):

        # Work here

        print(watcher_context.execution_id)
        print(watcher_context.pipeline_id)
        print(watcher_context.watermark)
        print(watcher_context.next_watermark)

        return ETLResults(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
        )
        

Hiearchical Executions
-----------------------

You can log hierarchical executions by using the ``track_pipeline_execution`` decorator.
You can provide child processes the parent execution id from the WatcherExecutionContext.

.. code-block:: python

    from watcher import Watcher, WatcherExecutionContext

    watcher = Watcher("https://api.watcher.example.com")

    synced_parent_config = watcher.sync_pipeline_config(MY_PARENT_PIPELINE_CONFIG)

    @watcher.track_pipeline_execution(
        pipeline_id=synced_parent_config.pipeline.id, 
        active=synced_parent_config.active)
    def my_parent_pipeline(watcher_context: WatcherExecutionContext):

        synced_child_config = watcher.sync_pipeline_config(MY_CHILD_PIPELINE_CONFIG)

        @watcher.track_pipeline_execution(
            pipeline_id=synced_child_config.pipeline.id, 
            active=synced_child_config.active
            parent_execution_id=watcher_context.execution_id)
        child_pipeline():

            # Work here

            return ETLResults(
                completed_successfully=True,
                inserts=100,
                total_rows=100,
            )
        
        return ETLResults(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
        )

    my_parent_pipeline()

Active Flag
-----------

You can set a Pipeline's active flag to False to skip the execution. This is normally triggered 
through the Watcher framework directly as the active flag is received from the Watcher API.

.. code-block:: python

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active)
    def my_pipeline(watcher_context: WatcherExecutionContext):

        # Function IS SKIPPED if active is False

        return ETLResults(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
        )

    my_pipeline()

.. note::
    This can be a useful functionality to use in your pipelines to skip executions if needed.