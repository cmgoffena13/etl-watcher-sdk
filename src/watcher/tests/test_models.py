import pytest
from pydantic import ValidationError

from watcher.models.address_lineage import Address, AddressLineage
from watcher.models.execution import (
    ETLResults,
    ExecutionResult,
    WatcherExecutionContext,
)
from watcher.models.pipeline import (
    Pipeline,
    PipelineConfig,
    SyncedPipelineConfig,
    _PipelineWithResponse,
)


def test_etl_metrics_creation():
    """Test ETLResults creation with all fields."""
    metrics = ETLResults(
        completed_successfully=True,
        inserts=100,
        updates=50,
        soft_deletes=10,
        total_rows=1000,
        execution_metadata={"source": "database"},
    )

    assert metrics.completed_successfully is True
    assert metrics.inserts == 100
    assert metrics.updates == 50
    assert metrics.soft_deletes == 10
    assert metrics.total_rows == 1000
    assert metrics.execution_metadata == {"source": "database"}


def test_etl_metrics_optional_fields():
    """Test ETLResults with optional fields."""
    metrics = ETLResults(completed_successfully=False)

    assert metrics.completed_successfully is False
    assert metrics.inserts is None
    assert metrics.updates is None
    assert metrics.soft_deletes is None
    assert metrics.total_rows is None
    assert metrics.execution_metadata is None


def test_etl_metrics_validation():
    """Test ETLResults field validation."""
    # Test negative values are rejected
    with pytest.raises(ValidationError):
        ETLResults(completed_successfully=True, inserts=-1)

    with pytest.raises(ValidationError):
        ETLResults(completed_successfully=True, updates=-5)

    with pytest.raises(ValidationError):
        ETLResults(completed_successfully=True, soft_deletes=-2)

    with pytest.raises(ValidationError):
        ETLResults(completed_successfully=True, total_rows=-10)


def test_etl_metrics_inheritance():
    """Test extending ETLResults."""

    class CustomMetrics(ETLResults):
        custom_field: str = "test"
        another_field: int = 42

    metrics = CustomMetrics(
        completed_successfully=True, inserts=100, custom_field="hello"
    )

    assert metrics.completed_successfully is True
    assert metrics.inserts == 100
    assert metrics.custom_field == "hello"
    assert metrics.another_field == 42
    assert isinstance(metrics, ETLResults)


def test_execution_context_creation():
    """Test WatcherExecutionContext creation with all fields."""
    context = WatcherExecutionContext(
        execution_id=123,
        pipeline_id=456,
        watermark="2024-01-01",
        next_watermark="2024-01-02",
    )

    assert context.execution_id == 123
    assert context.pipeline_id == 456
    assert context.watermark == "2024-01-01"
    assert context.next_watermark == "2024-01-02"


def test_execution_context_optional_fields():
    """Test WatcherExecutionContext with optional fields."""
    context = WatcherExecutionContext(execution_id=123, pipeline_id=456)

    assert context.execution_id == 123
    assert context.pipeline_id == 456
    assert context.watermark is None
    assert context.next_watermark is None


def test_execution_context_validation():
    """Test WatcherExecutionContext field validation."""
    # Test required fields
    with pytest.raises(ValidationError):
        WatcherExecutionContext(execution_id=123)  # Missing pipeline_id

    with pytest.raises(ValidationError):
        WatcherExecutionContext(pipeline_id=456)  # Missing execution_id


def test_execution_result_creation():
    """Test ExecutionResult creation."""
    metrics = ETLResults(completed_successfully=True, inserts=100, total_rows=100)
    result = ExecutionResult(execution_id=123, results=metrics)

    assert result.execution_id == 123
    assert result.results == metrics
    assert result.results.inserts == 100


def test_pipeline_creation():
    """Test Pipeline creation."""
    pipeline = Pipeline(
        name="test-pipeline",
        pipeline_type_name="data-transformation",
    )

    assert pipeline.name == "test-pipeline"
    assert pipeline.pipeline_type_name == "data-transformation"


def test_pipeline_validation():
    """Test Pipeline field validation."""
    # Test required fields
    with pytest.raises(ValidationError):
        Pipeline(name="test")  # Missing pipeline_type_name

    with pytest.raises(ValidationError):
        Pipeline(pipeline_type_name="data-transformation")  # Missing name


def test_pipeline_optional_fields():
    """Test Pipeline with optional fields."""
    pipeline = Pipeline(
        name="test-pipeline",
        pipeline_type_name="data-transformation",
        pipeline_metadata={"version": "1.0"},
        freshness_number=30,
        timeliness_number=60,
    )

    assert pipeline.pipeline_metadata == {"version": "1.0"}
    assert pipeline.freshness_number == 30
    assert pipeline.timeliness_number == 60


def test_pipeline_config_creation():
    """Test PipelineConfig creation with watermark fields."""
    pipeline = Pipeline(
        name="test-pipeline",
        pipeline_type_name="data-transformation",
    )

    address_lineage = AddressLineage(
        source_addresses=[],
        target_addresses=[],
    )

    config = PipelineConfig(
        pipeline=pipeline,
        address_lineage=address_lineage,
        default_watermark="2024-01-01",
        next_watermark="2024-01-02",
    )

    assert config.pipeline.name == "test-pipeline"
    assert config.default_watermark == "2024-01-01"
    assert config.next_watermark == "2024-01-02"


def test_address_lineage_creation():
    """Test AddressLineage creation."""
    source = Address(
        name="source-db",
        address_type_name="database",
        address_type_group_name="rdbms",
    )
    target = Address(
        name="target-warehouse",
        address_type_name="data-warehouse",
        address_type_group_name="analytics",
    )

    lineage = AddressLineage(source_addresses=[source], target_addresses=[target])

    assert len(lineage.source_addresses) == 1
    assert len(lineage.target_addresses) == 1
    assert lineage.source_addresses[0].name == "source-db"
    assert lineage.target_addresses[0].name == "target-warehouse"


def test_address_lineage_validation():
    """Test AddressLineage field validation."""
    # Test required fields
    with pytest.raises(ValidationError):
        AddressLineage(source_addresses=[])  # Empty source_addresses

    with pytest.raises(ValidationError):
        AddressLineage(target_addresses=[])  # Empty target_addresses


def test_address_validation():
    """Test Address field validation."""
    with pytest.raises(ValidationError):
        Address(name="test")  # Missing required fields

    with pytest.raises(ValidationError):
        Address(
            name="test", address_type_name="database"
        )  # Missing address_type_group_name


def test_pipeline_config_creation():
    """Test PipelineConfig creation."""
    pipeline = Pipeline(name="test-pipeline", pipeline_type_name="data-transformation")

    source = Address(
        name="source-db",
        address_type_name="database",
        address_type_group_name="rdbms",
    )
    target = Address(
        name="target-warehouse",
        address_type_name="data-warehouse",
        address_type_group_name="analytics",
    )

    lineage = AddressLineage(source_addresses=[source], target_addresses=[target])

    config = PipelineConfig(pipeline=pipeline, address_lineage=lineage)

    assert config.pipeline == pipeline
    assert config.address_lineage == lineage


def test_pipeline_config_validation():
    """Test PipelineConfig field validation."""
    with pytest.raises(ValidationError):
        PipelineConfig(pipeline=None, address_lineage=None)


def test_synced_pipeline_config_creation():
    """Test SyncedPipelineConfig creation."""
    pipeline = _PipelineWithResponse(
        name="test-pipeline",
        pipeline_type_name="data-transformation",
        id=123,
        active=True,
    )

    source = Address(
        name="source-db",
        address_type_name="database",
        address_type_group_name="rdbms",
    )
    target = Address(
        name="target-warehouse",
        address_type_name="data-warehouse",
        address_type_group_name="analytics",
    )

    lineage = AddressLineage(source_addresses=[source], target_addresses=[target])

    config = SyncedPipelineConfig(
        pipeline=pipeline,
        address_lineage=lineage,
        watermark="2024-01-01",
        default_watermark="2024-01-01",
        next_watermark="2024-01-02",
    )

    assert config.pipeline == pipeline
    assert config.address_lineage == lineage
    assert config.watermark == "2024-01-01"
    assert config.pipeline.id == 123
    assert config.pipeline.active is True


def test_synced_pipeline_config_inactive():
    """Test SyncedPipelineConfig with inactive pipeline."""
    pipeline = _PipelineWithResponse(
        name="test-pipeline",
        pipeline_type_name="data-transformation",
        id=123,
        active=False,
    )

    source = Address(
        name="source-db",
        address_type_name="database",
        address_type_group_name="rdbms",
    )
    target = Address(
        name="target-warehouse",
        address_type_name="data-warehouse",
        address_type_group_name="analytics",
    )

    lineage = AddressLineage(source_addresses=[source], target_addresses=[target])

    config = SyncedPipelineConfig(
        pipeline=pipeline,
        address_lineage=lineage,
        watermark="2024-01-01",
        default_watermark="2024-01-01",
        next_watermark="2024-01-02",
    )

    assert config.pipeline.id == 123
    assert config.pipeline.active is False
