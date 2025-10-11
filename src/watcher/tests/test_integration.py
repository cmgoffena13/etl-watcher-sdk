from unittest.mock import Mock, patch

import pytest

from watcher.models.address_lineage import Address, AddressLineage
from watcher.models.execution import ETLResult, WatcherExecutionContext
from watcher.models.pipeline import Pipeline, PipelineConfig, SyncedPipelineConfig


@pytest.fixture
def integration_pipeline():
    """Create a complete pipeline configuration for integration testing."""
    return Pipeline(
        name="integration-test-pipeline",
        pipeline_type_name="data-transformation",
        default_watermark="2024-01-01",
        next_watermark="2024-01-02",
    )


@pytest.fixture
def integration_address_lineage():
    """Create address lineage for integration testing."""
    return AddressLineage(
        source_addresses=[
            Address(
                name="source-database",
                address_type_name="database",
                address_type_group_name="rdbms",
            )
        ],
        target_addresses=[
            Address(
                name="target-warehouse",
                address_type_name="data-warehouse",
                address_type_group_name="analytics",
            )
        ],
    )


@pytest.fixture
def integration_config(integration_pipeline, integration_address_lineage):
    """Create complete pipeline config for integration testing."""
    return PipelineConfig(
        pipeline=integration_pipeline, address_lineage=integration_address_lineage
    )


@patch("watcher.client.Watcher._make_request_with_retry")
def test_complete_etl_workflow(
    mock_make_request_with_retry, watcher_client, integration_config
):
    """Test complete ETL workflow from sync to execution."""
    # Mock successful pipeline sync
    mock_pipeline_response = Mock()
    mock_pipeline_response.json.return_value = {
        "id": 123,
        "active": True,
        "load_lineage": True,
        "watermark": "2024-01-01",
    }
    mock_pipeline_response.raise_for_status.return_value = None

    # Mock successful address lineage sync
    mock_lineage_response = Mock()
    mock_lineage_response.raise_for_status.return_value = None

    # Mock execution start
    mock_execution_start = Mock()
    mock_execution_start.json.return_value = {"id": 456}
    mock_execution_start.raise_for_status.return_value = None

    # Mock execution end
    mock_execution_end = Mock()
    mock_execution_end.raise_for_status.return_value = None

    mock_make_request_with_retry.side_effect = [
        mock_pipeline_response,  # Pipeline sync
        mock_lineage_response,  # Address lineage sync
        mock_execution_start,  # Start execution
        mock_execution_end,  # End execution
    ]

    # Step 1: Sync pipeline configuration
    synced_config = watcher_client.sync_pipeline_config(integration_config)
    assert isinstance(synced_config, SyncedPipelineConfig)
    assert synced_config.pipeline.active is True
    assert synced_config.watermark == "2024-01-01"

    # Step 2: Define ETL function with execution tracking
    @watcher_client.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id,
        active=synced_config.pipeline.active,
        watermark=synced_config.watermark,
        next_watermark="2024-01-02",
    )
    def etl_pipeline(watcher_context: WatcherExecutionContext):
        # Verify context is properly injected
        assert isinstance(watcher_context, WatcherExecutionContext)
        assert watcher_context.pipeline_id == synced_config.pipeline.id
        assert watcher_context.watermark == "2024-01-01"
        assert watcher_context.next_watermark == "2024-01-02"

        # Simulate ETL work
        return ETLResult(
            completed_successfully=True,
            inserts=1000,
            updates=200,
            total_rows=1200,
            execution_metadata={"source": "database", "target": "warehouse"},
        )

    # Step 3: Execute ETL pipeline
    result = etl_pipeline()

    # Verify execution was tracked
    assert result is not None
    assert hasattr(result, "execution_id")
    assert hasattr(result, "results")
    assert result.results.inserts == 1000
    assert result.results.total_rows == 1200

    # Verify all API calls were made
    assert mock_make_request_with_retry.call_count == 4


@patch("watcher.client.Watcher._make_request_with_retry")
def test_pipeline_chaining_workflow(
    mock_make_request_with_retry, watcher_client, integration_address_lineage
):
    """Test pipeline chaining workflow."""
    # Mock responses for parent pipeline
    mock_parent_pipeline = Mock()
    mock_parent_pipeline.json.return_value = {
        "id": 100,
        "active": True,
        "load_lineage": True,
        "watermark": "2024-01-01",
    }
    mock_parent_pipeline.raise_for_status.return_value = None

    mock_parent_lineage = Mock()
    mock_parent_lineage.raise_for_status.return_value = None

    # Mock execution responses
    mock_execution_start = Mock()
    mock_execution_start.json.return_value = {"id": 456}
    mock_execution_start.raise_for_status.return_value = None

    mock_execution_end = Mock()
    mock_execution_end.raise_for_status.return_value = None

    mock_make_request_with_retry.side_effect = [
        mock_parent_pipeline,  # Parent pipeline sync
        mock_parent_lineage,  # Parent address lineage sync
        mock_execution_start,  # Start parent execution
        mock_execution_end,  # End parent execution
    ]

    # Create parent pipeline config
    parent_config = PipelineConfig(
        pipeline=Pipeline(
            name="parent-pipeline",
            pipeline_type_name="data-extraction",
            default_watermark="2024-01-01",
        ),
        address_lineage=integration_address_lineage,
    )

    # Sync parent pipeline
    synced_parent = watcher_client.sync_pipeline_config(parent_config)

    # Define parent pipeline with execution tracking
    @watcher_client.track_pipeline_execution(
        pipeline_id=synced_parent.pipeline.id, active=synced_parent.pipeline.active
    )
    def parent_pipeline(watcher_context: WatcherExecutionContext):
        return ETLResult(completed_successfully=True, inserts=500, total_rows=500)

    # Execute parent pipeline
    parent_result = parent_pipeline()
    assert parent_result is not None
    assert parent_result.execution_id == 456

    # Verify API calls were made
    assert mock_make_request_with_retry.call_count == 4


@patch("watcher.client.Watcher._make_request_with_retry")
def test_inactive_pipeline_workflow(
    mock_make_request_with_retry, watcher_client, integration_config
):
    """Test workflow with inactive pipeline."""
    # Mock inactive pipeline response
    mock_response = Mock()
    mock_response.json.return_value = {
        "id": 123,
        "active": False,
        "load_lineage": True,
        "watermark": None,
    }
    mock_response.raise_for_status.return_value = None
    mock_make_request_with_retry.return_value = mock_response

    # Sync inactive pipeline
    synced_config = watcher_client.sync_pipeline_config(integration_config)
    assert synced_config.pipeline.active is False
    assert synced_config.watermark is None  # Inactive pipelines have no watermark

    # Define ETL function for inactive pipeline
    @watcher_client.track_pipeline_execution(
        pipeline_id=synced_config.pipeline.id, active=synced_config.pipeline.active
    )
    def etl_inactive():
        return ETLResult(completed_successfully=True, inserts=100, total_rows=100)

    # Execute should return None for inactive pipeline
    result = etl_inactive()
    assert result is None

    # Only pipeline sync call should be made, no execution calls
    assert mock_make_request_with_retry.call_count == 1


@patch("watcher.client.Watcher._make_request_with_retry")
def test_custom_metrics_workflow(mock_make_request_with_retry, watcher_client):
    """Test workflow with custom ETLResult."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_end = Mock()
    mock_end.raise_for_status.return_value = None

    mock_make_request_with_retry.side_effect = [mock_start, mock_end]

    class CustomMetrics(ETLResult):
        custom_field: str = "test"
        processing_time: float = 0.0

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def etl_with_custom_metrics():
        return CustomMetrics(
            completed_successfully=True,
            inserts=100,
            total_rows=100,
            custom_field="hello",
            processing_time=1.5,
        )

    # This should work with custom metrics
    result = etl_with_custom_metrics()
    assert result is not None
    assert hasattr(result, "results")
    assert result.results.custom_field == "hello"
    assert result.results.processing_time == 1.5
