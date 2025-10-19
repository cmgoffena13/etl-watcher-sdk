# [Watcher](https://github.com/cmgoffena13/etl-watcher) SDK

[![PyPI version](https://badge.fury.io/py/etl-watcher-sdk.svg)](https://pypi.org/project/etl-watcher-sdk/)
[![Changelog](https://img.shields.io/badge/changelog-0.1.24-blue.svg)](CHANGELOG.md)

## QuickStart

### Installation

You can install the Watcher SDK, `etl-watcher-sdk`, using your preferred package manager.

### Store Pipeline and Address Lineage Configuration

Store your pipeline and address lineage configuration in a Python file.

```python
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
```

### Sync Pipeline and Address Lineage Configuration

Sync your pipeline and address lineage configuration to the Watcher framework. 
This ensures your code is the source of truth for the pipeline and address lineage configuration.

```python
from watcher import Watcher, PipelineConfig

watcher = Watcher("https://api.watcher.example.com")
synced_config = watcher.sync_pipeline_config(MY_ETL_PIPELINE_CONFIG)
print(f"Pipeline synced!")
```

### Track Pipeline Execution

```python
from watcher import Watcher, PipelineConfig, ETLResult

watcher = Watcher("https://api.watcher.example.com")

synced_config = watcher.sync_pipeline_config(MY_ETL_PIPELINE_CONFIG)

@watcher.track_pipeline_execution(
    pipeline_id=synced_config.pipeline.id, 
    active=synced_config.pipeline.active
)
def etl_pipeline():
    print("Starting ETL pipeline")
    
    # Your ETL work here
    # Set completed_successfully=True/False based on your logic
    
    return ETLResult(
        completed_successfully=True,
        inserts=100,
        total_rows=100,
        execution_metadata={"partition": "2025-01-01"},
    )

etl_pipeline()
```

## Contributing

I welcome contributions to the Watcher SDK! Please see the [Contributing Guidelines](CONTRIBUTING.md) for details on how to get started, the development process, and how to submit pull requests.

### Quick Start for Contributors
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Spin up the [Watcher framework](https://github.com/cmgoffena13/etl-watcher) for manual integration testing
5. Run tests in the repo with `make test`
6. Submit a pull request

For detailed information about the coding standards, testing requirements, and contribution process, please refer to the [Contributing Guidelines](CONTRIBUTING.md).