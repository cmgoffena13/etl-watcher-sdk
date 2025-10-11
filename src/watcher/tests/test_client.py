"""
Tests for the Watcher client functionality.
"""

from unittest.mock import Mock, patch

import httpx
import pytest

from watcher.client import Watcher
from watcher.models.address_lineage import Address, AddressLineage
from watcher.models.execution import ETLResult, WatcherContext
from watcher.models.pipeline import Pipeline, PipelineConfig, SyncedPipelineConfig


def test_watcher_initialization():
    """Test Watcher client initialization."""
    watcher = Watcher("https://api.example.com")
    assert watcher.base_url == "https://api.example.com"
    assert isinstance(watcher.client, httpx.Client)


@patch("watcher.client.Watcher._make_request_with_retry")
def test_sync_pipeline_config_success(
    mock_make_request_with_retry, watcher_client, sample_pipeline_config
):
    """Test successful pipeline sync."""
    # Mock API responses
    mock_pipeline_response = Mock()
    mock_pipeline_response.json.return_value = {
        "id": 123,
        "active": True,
        "load_lineage": True,
        "watermark": "2024-01-01",
    }
    mock_pipeline_response.raise_for_status.return_value = None

    mock_lineage_response = Mock()
    mock_lineage_response.raise_for_status.return_value = None

    mock_make_request_with_retry.side_effect = [
        mock_pipeline_response,
        mock_lineage_response,
    ]

    result = watcher_client.sync_pipeline_config(sample_pipeline_config)

    assert isinstance(result, SyncedPipelineConfig)
    assert result.pipeline.active is True
    assert result.watermark == "2024-01-01"
    assert mock_make_request_with_retry.call_count == 2  # Pipeline + address lineage


@patch("watcher.client.Watcher._make_request_with_retry")
def test_sync_pipeline_config_inactive(
    mock_make_request_with_retry, watcher_client, sample_pipeline_config
):
    """Test pipeline sync when pipeline is inactive."""
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

    result = watcher_client.sync_pipeline_config(sample_pipeline_config)

    assert isinstance(result, SyncedPipelineConfig)
    assert result.pipeline.active is False
    assert result.watermark is None  # Inactive pipelines have no watermark
    assert (
        mock_make_request_with_retry.call_count == 1
    )  # Only pipeline call, no lineage


@patch("watcher.client.Watcher._make_request_with_retry")
def test_sync_pipeline_config_no_lineage(
    mock_make_request_with_retry, watcher_client, sample_pipeline_config
):
    """Test pipeline sync when load_lineage is False."""
    # Mock pipeline response with load_lineage=False
    mock_response = Mock()
    mock_response.json.return_value = {
        "id": 123,
        "active": True,
        "load_lineage": False,
        "watermark": "2024-01-01",
    }
    mock_response.raise_for_status.return_value = None
    mock_make_request_with_retry.return_value = mock_response

    result = watcher_client.sync_pipeline_config(sample_pipeline_config)

    assert isinstance(result, SyncedPipelineConfig)
    assert result.pipeline.active is True
    assert mock_make_request_with_retry.call_count == 1  # Only pipeline call


@patch("watcher.client.Watcher._make_request_with_retry")
def test_track_pipeline_execution_decorator_without_context(
    mock_make_request_with_retry, watcher_client
):
    """Test execution decorator without watcher_context parameter."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_end = Mock()
    mock_end.raise_for_status.return_value = None

    mock_make_request_with_retry.side_effect = [mock_start, mock_end]

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def simple_etl():
        return ETLResult(completed_successfully=True, inserts=100, total_rows=100)

    # This should work without watcher_context parameter
    result = simple_etl()
    assert result is not None


@patch("watcher.client.Watcher._make_request_with_retry")
def test_track_pipeline_execution_decorator_with_context(
    mock_make_request_with_retry, watcher_client
):
    """Test execution decorator with watcher_context parameter."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_end = Mock()
    mock_end.raise_for_status.return_value = None

    mock_make_request_with_retry.side_effect = [mock_start, mock_end]

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def etl_with_context(watcher_context: WatcherContext):
        assert isinstance(watcher_context, WatcherContext)
        assert watcher_context.pipeline_id == 123
        return ETLResult(completed_successfully=True, inserts=100, total_rows=100)

    # This should work with watcher_context parameter
    result = etl_with_context()
    assert result is not None


def test_track_pipeline_execution_inactive_pipeline(watcher_client):
    """Test execution decorator with inactive pipeline."""

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=False)
    def etl_inactive():
        return ETLResult(completed_successfully=True, inserts=100, total_rows=100)

    # Should return None for inactive pipeline
    result = etl_inactive()
    assert result is None


@patch("watcher.client.Watcher._make_request_with_retry")
def test_etl_metrics_validation(mock_make_request_with_retry, watcher_client):
    """Test ETLResult validation in decorator."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_end = Mock()
    mock_end.raise_for_status.return_value = None

    mock_make_request_with_retry.side_effect = [mock_start, mock_end]

    class CustomMetrics(ETLResult):
        custom_field: str = "test"

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def etl_with_custom_metrics():
        return CustomMetrics(
            completed_successfully=True, inserts=100, custom_field="hello"
        )

    # Should work with inherited ETLResult
    result = etl_with_custom_metrics()
    assert result is not None


@patch("watcher.client.Watcher._make_request_with_retry")
def test_etl_metrics_validation_failure(mock_make_request_with_retry, watcher_client):
    """Test ETLResult validation failure."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_make_request_with_retry.return_value = mock_start

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def etl_invalid_return():
        return {"inserts": 100}  # Not ETLResult

    # Should raise ValueError for invalid return type
    with pytest.raises(ValueError, match="Function must return ETLResult"):
        etl_invalid_return()


@patch("watcher.client.Watcher._make_request_with_retry")
def test_execution_error_handling(mock_make_request_with_retry, watcher_client):
    """Test execution error handling."""
    # Mock API failure
    mock_make_request_with_retry.side_effect = httpx.HTTPError("API Error")

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def etl_with_error():
        return ETLResult(completed_successfully=True, inserts=100)

    # Should propagate the HTTP error
    with pytest.raises(httpx.HTTPError):
        etl_with_error()


def test_execution_context_fields():
    """Test WatcherContext contains expected fields."""
    context = WatcherContext(
        execution_id=123,
        pipeline_id=456,
        watermark="2024-01-01",
        next_watermark="2024-01-02",
    )

    assert context.execution_id == 123
    assert context.pipeline_id == 456
    assert context.watermark == "2024-01-01"
    assert context.next_watermark == "2024-01-02"


def test_etl_metrics_fields():
    """Test ETLResult contains expected fields."""
    metrics = ETLResult(
        completed_successfully=True,
        inserts=100,
        updates=50,
        soft_deletes=10,
        total_rows=1000,
        execution_metadata={"source": "database"},
    )

    assert metrics.inserts == 100
    assert metrics.updates == 50
    assert metrics.soft_deletes == 10
    assert metrics.total_rows == 1000
    assert metrics.execution_metadata == {"source": "database"}


def test_pipeline_config_creation():
    """Test PipelineConfig creation and validation."""
    config = PipelineConfig(
        pipeline=Pipeline(
            name="test-pipeline",
            pipeline_type_name="data-transformation",
            default_watermark="2024-01-01",
        ),
        address_lineage=AddressLineage(
            source_addresses=[
                Address(
                    name="source-db",
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
        ),
    )

    assert config.pipeline.name == "test-pipeline"
    assert len(config.address_lineage.source_addresses) == 1
    assert len(config.address_lineage.target_addresses) == 1
