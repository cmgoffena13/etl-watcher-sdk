Address Management
====================

This guide will show you how to manage addresses for your pipelines.

Address Lineage Configuration
------------------------------

The Address Lineage Configuration is an optional configuration you can add to PipelineConfig.
This is used to store the address lineage for your pipeline.

.. code-block:: python

    from watcher import AddressLineage, Address, Pipeline, PipelineConfig

    MY_PIPELINE_CONFIG = PipelineConfig(
        pipeline=Pipeline(
            name="my-pipeline",
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

Loading Address Lineage
------------------------

Address Lineage is loaded automatically when the pipeline is synced if the load_lineage flag is set to True. 
The load_lineage flag is created as True upon first creation of the pipeline. After a successful execution, 
the load_lineage flag is set to False. It can be set to True again through the Watcher framework API.

.. code-block:: python

    from watcher import Watcher, PipelineConfig

    watcher = Watcher("https://api.watcher.example.com")

    synced_config = watcher.sync_pipeline_config(MY_PIPELINE_CONFIG)


