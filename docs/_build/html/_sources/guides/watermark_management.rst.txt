Watermark Management
====================

This guide will show you how to manage watermarks for your pipelines.

Incrementing Watermarks
-----------------------

Watermarks are used to track the progress of your pipelines.

You can increment the watermark by providing the next watermark 
to your Pipeline Config before syncing with the Watcher framework.


.. code-block:: python

    import pendulum
    from watcher import Watcher, Pipeline, PipelineConfig, AddressLineage, Address

    watcher = Watcher("https://api.watcher.example.com")

    MY_ETL_PIPELINE_CONFIG = PipelineConfig(
        pipeline=Pipeline(
            name="my-etl-pipeline",
            pipeline_type_name="extraction",
        ),
        default_watermark="2024-01-01",
        address_lineage=AddressLineage(
            source_addresses=[
                Address(
                    name="source_db.source_schema.source_table",
                    address_type_name="postgres",
                    address_type_group_name="database",
                )
            ],
            target_addresses=[
                Address(
                    name="target_db.target_schema.target_table",
                    address_type_name="snowflake",
                    address_type_group_name="warehouse",
                )
            ],
        ),
    )

    MY_ETL_PIPELINE_CONFIG.next_watermark = pendulum.now("UTC").date().to_date_string()
        
    synced_config = watcher.sync_pipeline_config(MY_ETL_PIPELINE_CONFIG)
    print(f"Pipeline synced! New Watermark: {synced_config.watermark}")


For the first run, the watermark will be the default watermark. Then, it will be the next watermark. 
If you cannot set the next watermark before your pipeline execution, 
you can update the next_watermark value once you have it within your pipeline run using the 
``update_pipeline_next_watermark()`` method.  

.. note::
    It is important to be aware of inclusivity / exlusivity to make sure your incremental windows do not overlap.

Accessing Watermarks
--------------------

You can access the watermarks for your pipelines by using the WatcherContext.

.. code-block:: python
    
    from watcher import Watcher, PipelineConfig, WatcherContext

    watcher = Watcher("https://api.watcher.example.com")

    MY_ETL_PIPELINE_CONFIG.next_watermark = pendulum.now("UTC").date().to_date_string()
        
    synced_config = watcher.sync_pipeline_config(MY_ETL_PIPELINE_CONFIG)

    @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active
        watermark=synced_config.watermark
        next_watermark=synced_config.next_watermark
        )
    def etl_pipeline(watcher_context: WatcherContext):
        print(f"Watermark: {watcher_context.watermark}")
        print(f"Next Watermark: {watcher_context.next_watermark}")

        query = f"""
            SELECT
            *
            FROM Table_A
            WHERE date_column < '{watcher_context.next_watermark}'
                AND date_column >= '{watcher_context.watermark}'
        """
        
        return ETLResult(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
            execution_metadata={"partition": "2025-01-01"},
        )

    etl_pipeline()

Watermark Data Type
--------------------

The watermark data type is stored as a string in the Watcher framework to allow for flexibility.
It is important to be aware of the data types you are using in your code 
and to properly cast it once accessed from the WatcherContext.