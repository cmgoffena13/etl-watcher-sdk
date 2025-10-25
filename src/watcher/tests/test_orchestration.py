from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from watcher import ETLResult, PipelineConfig, WatcherContext
from watcher.models.pipeline import Pipeline
from watcher.orchestration import (
    OrchestratedETL,
    OrchestrationContext,
)


def test_orchestration_context_basic():
    """Test basic context creation."""
    context = OrchestrationContext(
        orchestrator="dagster", run_id="test_run_123", partition_key="2024-01-01"
    )

    assert context.orchestrator == "dagster"
    assert context.run_id == "test_run_123"
    assert context.partition_key == "2024-01-01"


def test_orchestration_context_to_dict():
    """Test context to dictionary conversion."""
    context = OrchestrationContext(
        orchestrator="airflow",
        run_id="test_run_456",
        execution_date=datetime(2024, 1, 1),
        dag_id="test_dag",
        task_id="test_task",
        custom_field="custom_value",
    )

    result = context.to_dict()

    assert result["orchestrator"] == "airflow"
    assert result["run_id"] == "test_run_456"
    assert result["execution_date"] == "2024-01-01 00:00:00"
    assert result["dag_id"] == "test_dag"
    assert result["task_id"] == "test_task"
    assert result["custom_field"] == "custom_value"


@pytest.fixture
def pipeline_config():
    """Sample pipeline configuration."""
    return PipelineConfig(
        pipeline=Pipeline(name="test_pipeline", pipeline_type_name="test_type")
    )


@pytest.fixture
def etl_function():
    """Sample ETL function."""

    def etl_func(watcher_context: WatcherContext, **kwargs):
        return ETLResult(
            completed_successfully=True,
            inserts=100,
            total_rows=1000,
            execution_metadata={"test": "metadata"},
        )

    return etl_func


@patch("watcher.orchestration.Watcher")
def test_orchestrated_etl_init(mock_watcher_class, pipeline_config):
    """Test OrchestratedETL initialization."""
    mock_watcher = Mock()
    mock_watcher_class.return_value = mock_watcher

    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    assert etl.watcher == mock_watcher
    assert etl.pipeline_config == pipeline_config
    assert etl._synced_config is None


@patch("watcher.orchestration.Watcher")
def test_detect_dagster_context(mock_watcher_class, pipeline_config):
    """Test Dagster context detection."""
    mock_watcher = Mock()
    mock_watcher_class.return_value = mock_watcher

    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    # Mock Dagster context
    dagster_context = Mock()
    dagster_context.run_id = "dagster_run_123"
    dagster_context.partition_key = "2024-01-01"
    dagster_context.dag_id = "test_dag"
    dagster_context.task_id = "test_task"

    context = etl._detect_orchestration_context(dagster_context)

    assert context.orchestrator == "dagster"
    assert context.run_id == "dagster_run_123"
    assert context.partition_key == "2024-01-01"
    assert context.dag_id == "test_dag"
    assert context.task_id == "test_task"


@patch("watcher.orchestration.Watcher")
def test_detect_airflow_dict_context(mock_watcher_class, pipeline_config):
    """Test Airflow dict context detection."""
    mock_watcher = Mock()
    mock_watcher_class.return_value = mock_watcher

    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    # Mock Airflow context (dict)
    airflow_context = {
        "run_id": "airflow_run_456",
        "execution_date": datetime(2024, 1, 1),
        "dag_id": "test_dag",
        "task_id": "test_task",
    }

    context = etl._detect_orchestration_context(airflow_context)

    assert context.orchestrator == "airflow"
    assert context.run_id == "airflow_run_456"
    assert context.execution_date == datetime(2024, 1, 1)
    assert context.dag_id == "test_dag"
    assert context.task_id == "test_task"


@patch("watcher.orchestration.Watcher")
def test_detect_airflow_object_context(mock_watcher_class, pipeline_config):
    """Test Airflow object context detection."""
    mock_watcher = Mock()
    mock_watcher_class.return_value = mock_watcher

    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    # Mock Airflow context (object) - make sure it doesn't have run_id to avoid Dagster detection
    airflow_context = Mock()
    airflow_context.execution_date = datetime(2024, 1, 1)
    airflow_context.dag_id = "test_dag"
    airflow_context.task_id = "test_task"
    # Explicitly delete run_id to avoid Dagster detection
    del airflow_context.run_id

    context = etl._detect_orchestration_context(airflow_context)

    assert context.orchestrator == "airflow"
    assert context.run_id is None
    assert context.execution_date == datetime(2024, 1, 1)
    assert context.dag_id == "test_dag"
    assert context.task_id == "test_task"


@patch("watcher.orchestration.Watcher")
def test_detect_unknown_context(mock_watcher_class, pipeline_config):
    """Test unknown context detection."""
    mock_watcher = Mock()
    mock_watcher_class.return_value = mock_watcher

    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    # Mock unknown context
    unknown_context = "some_unknown_context"

    with pytest.warns(UserWarning, match="Unknown orchestration context"):
        context = etl._detect_orchestration_context(unknown_context)

    assert context.orchestrator == "unknown"
    assert context.run_id == str(id(unknown_context))


@patch("watcher.orchestration.Watcher")
def test_execute_etl_with_dagster_context(
    mock_watcher_class, pipeline_config, etl_function
):
    """Test ETL execution with Dagster context."""
    # Mock Watcher and synced config
    mock_watcher = Mock()
    mock_synced_config = Mock()
    mock_synced_config.pipeline.id = 123
    mock_synced_config.pipeline.active = True
    mock_synced_config.watermark = "2024-01-01"
    mock_synced_config.next_watermark = None
    mock_watcher.sync_pipeline_config.return_value = mock_synced_config
    mock_watcher_class.return_value = mock_watcher

    # Mock the decorator
    def mock_decorator(*args, **kwargs):
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Simulate the decorator behavior
                watcher_context = WatcherContext(
                    execution_id=456, pipeline_id=123, watermark="2024-01-01"
                )
                return func(watcher_context, **kwargs)

            return wrapper

        return decorator

    mock_watcher.track_pipeline_execution = mock_decorator

    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    # Mock Dagster context
    dagster_context = Mock()
    dagster_context.run_id = "dagster_run_123"
    dagster_context.partition_key = "2024-01-01"

    result = etl.execute_etl(etl_function, dagster_context)

    assert isinstance(result, ETLResult)
    assert result.completed_successfully is True
    assert result.inserts == 100
    assert result.total_rows == 1000
    assert "orchestrator" in result.execution_metadata
    assert result.execution_metadata["orchestrator"] == "dagster"


@patch("watcher.orchestration.Watcher")
def test_execute_etl_with_airflow_context(
    mock_watcher_class, pipeline_config, etl_function
):
    """Test ETL execution with Airflow context."""
    # Mock Watcher and synced config
    mock_watcher = Mock()
    mock_synced_config = Mock()
    mock_synced_config.pipeline.id = 123
    mock_synced_config.pipeline.active = True
    mock_synced_config.watermark = "2024-01-01"
    mock_synced_config.next_watermark = None
    mock_watcher.sync_pipeline_config.return_value = mock_synced_config
    mock_watcher_class.return_value = mock_watcher

    # Mock the decorator
    def mock_decorator(*args, **kwargs):
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Simulate the decorator behavior
                watcher_context = WatcherContext(
                    execution_id=456, pipeline_id=123, watermark="2024-01-01"
                )
                return func(watcher_context, **kwargs)

            return wrapper

        return decorator

    mock_watcher.track_pipeline_execution = mock_decorator

    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    # Mock Airflow context
    airflow_context = {
        "run_id": "airflow_run_456",
        "execution_date": datetime(2024, 1, 1),
        "dag_id": "test_dag",
        "task_id": "test_task",
    }

    result = etl.execute_etl(etl_function, airflow_context)

    assert isinstance(result, ETLResult)
    assert result.completed_successfully is True
    assert result.inserts == 100
    assert result.total_rows == 1000
    assert "orchestrator" in result.execution_metadata
    assert result.execution_metadata["orchestrator"] == "airflow"


@patch("watcher.orchestration.Watcher")
def test_execute_etl_invalid_return_type(mock_watcher_class, pipeline_config):
    """Test ETL execution with invalid return type."""
    # Mock Watcher and synced config
    mock_watcher = Mock()
    mock_synced_config = Mock()
    mock_synced_config.pipeline.id = 123
    mock_synced_config.pipeline.active = True
    mock_synced_config.watermark = "2024-01-01"
    mock_synced_config.next_watermark = None
    mock_watcher.sync_pipeline_config.return_value = mock_synced_config
    mock_watcher_class.return_value = mock_watcher

    # Mock the decorator
    def mock_decorator(*args, **kwargs):
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Simulate the decorator behavior
                watcher_context = WatcherContext(
                    execution_id=456, pipeline_id=123, watermark="2024-01-01"
                )
                return func(watcher_context, **kwargs)

            return wrapper

        return decorator

    mock_watcher.track_pipeline_execution = mock_decorator

    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    # ETL function that returns invalid type
    def invalid_etl_func(watcher_context: WatcherContext):
        return "not_an_etl_result"

    with pytest.raises(ValueError, match="ETL function must return ETLResult"):
        etl.execute_etl(invalid_etl_func, None)


@patch("watcher.orchestration.Watcher")
def test_execute_etl_with_custom_context(
    mock_watcher_class, pipeline_config, etl_function
):
    """Test ETL execution with custom orchestration context."""
    # Mock Watcher and synced config
    mock_watcher = Mock()
    mock_synced_config = Mock()
    mock_synced_config.pipeline.id = 123
    mock_synced_config.pipeline.active = True
    mock_synced_config.watermark = "2024-01-01"
    mock_synced_config.next_watermark = None
    mock_watcher.sync_pipeline_config.return_value = mock_synced_config
    mock_watcher_class.return_value = mock_watcher

    # Mock the decorator
    def mock_decorator(*args, **kwargs):
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Simulate the decorator behavior
                watcher_context = WatcherContext(
                    execution_id=456, pipeline_id=123, watermark="2024-01-01"
                )
                return func(watcher_context, **kwargs)

            return wrapper

        return decorator

    mock_watcher.track_pipeline_execution = mock_decorator

    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    # Custom orchestration context
    custom_context = OrchestrationContext(
        orchestrator="custom", run_id="custom_run_789", custom_field="custom_value"
    )

    result = etl.execute_etl(etl_function, custom_context)

    assert isinstance(result, ETLResult)
    assert result.completed_successfully is True
    # The custom context should be injected into execution_metadata
    assert "orchestrator" in result.execution_metadata
    assert result.execution_metadata["orchestrator"] == "custom"
    assert result.execution_metadata["run_id"] == "custom_run_789"
    assert result.execution_metadata["custom_field"] == "custom_value"
