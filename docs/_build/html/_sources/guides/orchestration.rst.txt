Orchestration Integration
========================

The ETL Watcher SDK provides seamless integration with popular orchestration frameworks like Dagster and Airflow through the ``OrchestratedETL`` class.

Overview
--------

The orchestration integration allows you to:

- Use your existing ETL functions with orchestration frameworks
- Automatically inject orchestration context into your ETL metadata
- Maintain compatibility with both Dagster and Airflow
- Track ETL execution metrics through the Watcher API

Basic Usage
-----------

The ``OrchestratedETL`` class provides a unified interface for running ETL pipelines with orchestration context:

.. code-block:: python

    from watcher import OrchestratedETL, ETLResult, PipelineConfig, Pipeline

    # Define your ETL function
    def my_etl_function(watcher_context: WatcherContext, **kwargs):
        # Your ETL logic here
        data = extract_data()
        processed = transform_data(data)
        
        return ETLResult(
            completed_successfully=True,
            inserts=len(processed),
            total_rows=len(data),
            execution_metadata={"source": "database"}
        )

    # Create orchestrated ETL
    pipeline_config = PipelineConfig(
        pipeline=Pipeline(
            name="my_pipeline",
            pipeline_type_name="batch_etl"
        )
    )

    etl = OrchestratedETL(
        watcher_url="https://api.watcher.example.com",
        pipeline_config=pipeline_config
    )

    result = etl.execute_etl(my_etl_function)
    print(result)

Dagster Integration
------------------

For Dagster, you can use the ``OrchestratedETL`` class directly in your ops:

.. code-block:: python

    from dagster import op, job, OpExecutionContext
    from watcher import OrchestratedETL, ETLResult, PipelineConfig, Pipeline

    # Define your ETL function
    def extract_and_transform(watcher_context: WatcherContext, **kwargs) -> ETLResult:
        # Your ETL logic
        data = extract_data()
        processed = transform_data(data)
        
        return ETLResult(
            completed_successfully=True,
            inserts=len(processed),
            total_rows=len(data)
        )

    # Create Dagster op
    @op
    def my_etl_op(context: OpExecutionContext):
        etl = OrchestratedETL("https://api.watcher.com", pipeline_config)
        return etl.execute_etl(extract_and_transform, context)

Airflow Integration
-------------------

For Airflow, you can use the ``OrchestratedETL`` class in your tasks:

.. code-block:: python

    from airflow import DAG
    from airflow.operators.python import PythonOperator
    from watcher import OrchestratedETL, ETLResult, PipelineConfig, Pipeline

    # Define your ETL function
    def extract_and_transform(watcher_context: WatcherContext, **kwargs) -> ETLResult:
        # Your ETL logic
        data = extract_data()
        processed = transform_data(data)
        
        return ETLResult(
            completed_successfully=True,
            inserts=len(processed),
            total_rows=len(data)
        )

    # Create Airflow task
    def my_etl_task(**context):
        etl = OrchestratedETL("https://api.watcher.com", pipeline_config)
        return etl.execute_etl(extract_and_transform, context)

Advanced Usage
--------------

Watermark Management
~~~~~~~~~~~~~~~~~~~

The orchestration integration supports watermark management for incremental processing. Watermarks are automatically available in the `watcher_context`:

.. code-block:: python

    def my_etl_function(watcher_context: WatcherContext) -> ETLResult:
        # Access current watermark for incremental processing
        current_watermark = watcher_context.watermark
        next_watermark = watcher_context.next_watermark
        
        # Process data from watermark onwards
        data = extract_data_since(current_watermark, next_watermark)
        
        # The next watermark is automatically set by the SDK
        # based on the pipeline configuration
        
        return ETLResult(
            completed_successfully=True,
            inserts=len(data),
            total_rows=len(data)
        )

    # Execute ETL with orchestration context
    result = etl.execute_etl(my_etl_function, orchestration_context)

Context Detection
~~~~~~~~~~~~~~~~~

The ``OrchestratedETL`` class automatically detects orchestration context from:

- **Dagster**: ``OpExecutionContext`` objects with ``run_id`` and ``partition_key``
- **Airflow**: Dictionary or object contexts with ``dag_id`` and ``task_id``

Metadata Injection
~~~~~~~~~~~~~~~~~

Orchestration context is automatically injected into your ETL metadata:

.. code-block:: python

    # Dagster context automatically detected
    from dagster import op, OpExecutionContext
    
    @op
    def my_dagster_op(context: OpExecutionContext):
        etl = OrchestratedETL("https://api.watcher.com", pipeline_config)
        return etl.execute_etl(my_etl_function, context)
    
    # Airflow context automatically detected  
    from airflow.decorators import task
    
    @task
    def my_airflow_task(**context):
        etl = OrchestratedETL("https://api.watcher.com", pipeline_config)
        return etl.execute_etl(my_etl_function, context)

Error Handling
--------------

The orchestration integration handles errors gracefully:

- **Invalid Return Types**: Raises ``ValueError`` if ETL function doesn't return ``ETLResult``
- **Unknown Contexts**: Issues warnings for unrecognized orchestration contexts
- **API Failures**: Propagates Watcher API errors as expected

Best Practices
---------------

1. **Always Return ETLResult**: Your ETL functions must return ``ETLResult`` or a subclass
2. **Use Type Hints**: Add type hints for better IDE support and error detection
3. **Handle Errors**: Implement proper error handling in your ETL functions
4. **Test Integration**: Test your orchestration integration with mock contexts
5. **Monitor Metrics**: Use the injected orchestration metadata for monitoring

Example: Complete Dagster Pipeline with Parent Execution Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Track a parent execution that spans the entire workflow with child executions:

.. code-block:: python

    from dagster import op, job, OpExecutionContext
    from watcher import OrchestratedETL, ETLResult, PipelineConfig, Pipeline

    # Parent pipeline config
    parent_config = PipelineConfig(
        pipeline=Pipeline(
            name="user_data_pipeline",
            pipeline_type_name="etl_workflow"
        )
    )
    
    # Separate pipeline configs for each stage
    extract_config = PipelineConfig(
        pipeline=Pipeline(
            name="user_extract_pipeline",
            pipeline_type_name="extract"
        )
    )
    
    transform_config = PipelineConfig(
        pipeline=Pipeline(
            name="user_transform_pipeline", 
            pipeline_type_name="transform"
        )
    )
    
    load_config = PipelineConfig(
        pipeline=Pipeline(
            name="user_load_pipeline",
            pipeline_type_name="load"
        )
    )

    # Dagster ops with parent execution tracking
    @op
    def start_parent_execution(context: OpExecutionContext):
        """Start parent execution and return ID."""
        etl = OrchestratedETL("https://api.watcher.com", parent_config)
        return etl.start_parent_execution()

    @op
    def extract_op(context: OpExecutionContext, parent_execution_id: int):
        etl = OrchestratedETL("https://api.watcher.com", extract_config)
        return etl.execute_etl(extract_users, context, parent_execution_id=parent_execution_id)

    @op
    def transform_op(context: OpExecutionContext, parent_execution_id: int, extract_result: ETLResult):
        etl = OrchestratedETL("https://api.watcher.com", transform_config)
        return etl.execute_etl(transform_users, context, parent_execution_id=parent_execution_id)

    @op
    def load_op(context: OpExecutionContext, parent_execution_id: int, transform_result: ETLResult):
        etl = OrchestratedETL("https://api.watcher.com", load_config)
        return etl.execute_etl(load_users, context, parent_execution_id=parent_execution_id)

    @op
    def end_parent_execution(context: OpExecutionContext, parent_execution_id: int):
        """End the parent execution."""
        etl = OrchestratedETL("https://api.watcher.com", parent_config)
        
        summary_result = ETLResult(
            completed_successfully=True,
            execution_metadata={
                "execution_date": context.run_id
            }
        )
        etl.end_parent_execution(parent_execution_id, summary_result)
        
        return summary_result

    @job
    def user_data_pipeline():
        parent_id = start_parent_execution()
        extract_result = extract_op(parent_id)
        transform_result = transform_op(parent_id, extract_result)
        load_result = load_op(parent_id, transform_result)
        end_parent_execution(parent_id)

Example: Complete Airflow DAG with Parent Execution Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Track a parent execution that spans the entire workflow with child executions:

.. code-block:: python

    from airflow.decorators import dag, task
    
    def dag_failure_callback(context):
        """DAG failure callback to end parent execution on failure."""
        parent_execution_id = context['task_instance'].xcom_pull(task_ids='start_parent_execution')
        if parent_execution_id:
            etl = OrchestratedETL("https://api.watcher.com", parent_config)
            failure_result = ETLResult(
                completed_successfully=False
            )
            etl.end_parent_execution(parent_execution_id, failure_result)
    
    @dag(schedule_interval='@daily', on_failure_callback=dag_failure_callback)
    def etl_pipeline():
        @task
        def start_parent_execution():
            """Start parent execution and return ID."""
            etl = OrchestratedETL("https://api.watcher.com", parent_config)
            return etl.start_parent_execution() # Returns the parent execution ID
        
        @task
        def extract_task(parent_execution_id, **context):
            etl = OrchestratedETL("https://api.watcher.com", extract_config)
            return etl.execute_etl(extract_function, context, parent_execution_id=parent_execution_id)
        
        @task
        def transform_task(parent_execution_id, **context):
            etl = OrchestratedETL("https://api.watcher.com", transform_config)
            return etl.execute_etl(transform_function, context, parent_execution_id=parent_execution_id)
        
        @task
        def end_parent_execution(parent_execution_id, **context):
            """End the parent execution."""
            etl = OrchestratedETL("https://api.watcher.com", parent_config)
            
            summary_result = ETLResult(
                completed_successfully=True,
                execution_metadata={
                    "execution_date": context['ds'],
                    "dag_run_id": context['dag_run'].run_id
                }
            )
            etl.end_parent_execution(parent_execution_id, summary_result)
            
            return summary_result
        
        
        parent_id = start_parent_execution()
        extract = extract_task(parent_id)
        transform = transform_task(parent_id)
        end = end_parent_execution(parent_id)
        
        parent_id >> extract >> transform >> end
    
    etl_pipeline()