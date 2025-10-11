Quick Start Guide
=================

This guide will get you up and running with the Watcher SDK.

Installation
------------

You can install the Watcher SDK using your preferred package manager:

.. tabs::

   .. tab:: pip

      .. code-block:: bash

         pip install etl-watcher-sdk

   .. tab:: uv

      .. code-block:: bash

         uv add etl-watcher-sdk

   .. tab:: poetry

      .. code-block:: bash

         poetry add etl-watcher-sdk

Usage
------

Once you have the Watcher SDK installed, you can start using it to interact with the Watcher framework.

Store Pipeline and Address Lineage Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can store your pipeline and address lineage configuration in a Python file.

.. code-block:: python

   from watcher import Pipeline, PipelineConfig, AddressLineage, Address

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

Sync Pipeline and Address Lineage Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can sync your pipeline and address lineage configuration to the Watcher framework. 
This ensures your code is the source of truth for the pipeline and address lineage configuration.

.. warning::

   This will overwrite the pipeline and address lineage configuration in the Watcher framework.

.. code-block:: python

   from watcher import Watcher, PipelineConfig

   watcher = Watcher("https://api.watcher.example.com")
   synced_config = watcher.sync_pipeline_config(MY_ETL_PIPELINE_CONFIG)
   print(f"Pipeline synced!")


Track Pipeline Execution
~~~~~~~~~~~~~~~~~~~~~~~~

You can track and log the execution of your etl code by using the Watcher SDK.

.. code-block:: python

   from watcher import Watcher, PipelineConfig, ETLResults
   
   watcher = Watcher("https://api.watcher.example.com")

   synced_config = watcher.sync_pipeline_config(MY_ETL_PIPELINE_CONFIG)

   @watcher.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, 
        active=synced_config.pipeline.active
        )
   def etl_pipeline():
        print("Starting ETL pipeline")

        # Work

        return ETLResults(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
            execution_metadata={"partition": "2025-01-01"},
        )

   etl_pipeline()