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

.. code-block:: python

    from watcher import Watcher
    from watcher.models.execution import WatcherExecutionContext

    watcher = Watcher("https://api.watcher.example.com")

    synced_config = watcher.sync_pipeline_config(MY_ETL_PIPELINE_CONFIG)

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.active)
    def my_pipeline():


        # Work here

        return ETLMetrics(
            inserts=100,
            total_rows=100,
        )

    my_pipeline()

ETL Metrics
------------

The ETLMetrics is a class that is required to be returned from your pipeline function 
if using the ``track_pipeline_execution`` decorator.
It contains the metrics for your pipeline that are logged to the Watcher framework.

.. code-block:: python

    class ETLMetrics(BaseModel):
        inserts: Optional[int] = Field(default=None, ge=0)
        updates: Optional[int] = Field(default=None, ge=0)
        soft_deletes: Optional[int] = Field(default=None, ge=0)
        total_rows: Optional[int] = Field(default=None, ge=0)
        execution_metadata: Optional[dict] = None

Code Example:

.. code-block:: python

    from watcher.models.execution import ETLMetrics

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.active)
    def my_pipeline():


        # Work here

        return ETLMetrics(
            inserts=100,
            total_rows=100,
        )

Execution Results
-----------------

The ExecutionResults is a class that is returned from your pipeline function. This 
wraps around the ETLMetrics class and adds the execution id. This is to ensure access 
to the execution id for any usage. 

.. code-block:: python

    from watcher.models.execution import ExecutionResults

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.active)
    def my_pipeline() -> ExecutionResults:

        # Work here

        return ETLMetrics(
                inserts=100,
                total_rows=100,
            )

    results = my_pipeline()
    print(results.execution_id)
    print(results.metrics)
    print(results.metrics.inserts)

.. note::
    You can create another Pydantic model that inherits from ETLMetrics 
    and return that instead of ETLMetrics. Those fields will be accessible in 
    the ExecutionResults class that is returned from your pipeline function.

Watcher Execution Context
-----------------

The WatcherExecutionContext is a class that is passed to your pipeline function.
It contains the execution id, pipeline id, watermark, and next watermark variables. 
Your function must have `watcher_context` as a parameter if using the WatcherExecutionContext.

.. code-block:: python

    from watcher.models.execution import WatcherExecutionContext

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.active)
    def my_pipeline(watcher_context: WatcherExecutionContext):

        # Work here

        print(watcher_context.execution_id)
        print(watcher_context.pipeline_id)
        print(watcher_context.watermark)
        print(watcher_context.next_watermark)

        return ETLMetrics(
            inserts=100,
            total_rows=100,
        )
        

Hiearchical Executions
-----------------------

You can log hierarchical executions by using the ``track_pipeline_execution`` decorator.
You can provide child processes the parent execution id from the WatcherExecutionContext.

.. code-block:: python

    from watcher import Watcher
    from watcher.models.execution import WatcherExecutionContext

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

            return ETLMetrics(
                inserts=100,
                total_rows=100,
            )
        
        return ETLMetrics(
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
        active=synced_config.active)
    def my_pipeline(watcher_context: WatcherExecutionContext):

        # Function IS SKIPPED if active is False

        return ETLMetrics(
            inserts=100,
            total_rows=100,
        )

    my_pipeline()

.. note::
    This can be a useful functionality to use in your pipelines to skip executions if needed.