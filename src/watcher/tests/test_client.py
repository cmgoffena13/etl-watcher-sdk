"""
Tests for the Watcher client functionality.
"""

from unittest.mock import Mock, patch

import httpx
import pytest

from watcher.client import Watcher
from watcher.http_client import ProductionHTTPClient
from watcher.models.address_lineage import Address, AddressLineage
from watcher.models.execution import ETLResult, WatcherContext
from watcher.models.pipeline import Pipeline, PipelineConfig, SyncedPipelineConfig


def test_watcher_initialization():
    """Test Watcher client initialization."""
    watcher = Watcher("https://api.example.com")
    assert watcher.base_url == "https://api.example.com"
    assert isinstance(watcher.client, ProductionHTTPClient)


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_sync_pipeline_config_success(
    mock_request_with_retry, watcher_client, sample_pipeline_config
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

    mock_request_with_retry.side_effect = [
        mock_pipeline_response,
        mock_lineage_response,
    ]

    result = watcher_client.sync_pipeline_config(sample_pipeline_config)

    assert isinstance(result, SyncedPipelineConfig)
    assert result.pipeline.active is True
    assert result.watermark == "2024-01-01"
    assert mock_request_with_retry.call_count == 2  # Pipeline + address lineage


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_sync_pipeline_config_inactive(
    mock_request_with_retry, watcher_client, sample_pipeline_config
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
    mock_request_with_retry.return_value = mock_response

    result = watcher_client.sync_pipeline_config(sample_pipeline_config)

    assert isinstance(result, SyncedPipelineConfig)
    assert result.pipeline.active is False
    assert result.watermark is None  # Inactive pipelines have no watermark
    assert mock_request_with_retry.call_count == 1  # Only pipeline call, no lineage


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_sync_pipeline_config_no_lineage(
    mock_request_with_retry, watcher_client, sample_pipeline_config
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
    mock_request_with_retry.return_value = mock_response

    result = watcher_client.sync_pipeline_config(sample_pipeline_config)

    assert isinstance(result, SyncedPipelineConfig)
    assert result.pipeline.active is True
    assert mock_request_with_retry.call_count == 1  # Only pipeline call


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_track_pipeline_execution_decorator_without_context(
    mock_request_with_retry, watcher_client
):
    """Test execution decorator without watcher_context parameter."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_end = Mock()
    mock_end.raise_for_status.return_value = None

    mock_request_with_retry.side_effect = [mock_start, mock_end]

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def simple_etl():
        return ETLResult(completed_successfully=True, inserts=100, total_rows=100)

    # This should work without watcher_context parameter
    result = simple_etl()
    assert result is not None


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_track_pipeline_execution_decorator_with_context(
    mock_request_with_retry, watcher_client
):
    """Test execution decorator with watcher_context parameter."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_end = Mock()
    mock_end.raise_for_status.return_value = None

    mock_request_with_retry.side_effect = [mock_start, mock_end]

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


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_etl_metrics_validation(mock_request_with_retry, watcher_client):
    """Test ETLResult validation in decorator."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_end = Mock()
    mock_end.raise_for_status.return_value = None

    mock_request_with_retry.side_effect = [mock_start, mock_end]

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


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_etl_metrics_validation_failure(mock_request_with_retry, watcher_client):
    """Test ETLResult validation failure."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_request_with_retry.return_value = mock_start

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def etl_invalid_return():
        return {"inserts": 100}  # Not ETLResult

    # Should raise ValueError for invalid return type
    with pytest.raises(ValueError, match="Function must return ETLResult"):
        etl_invalid_return()


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_execution_error_handling(mock_request_with_retry, watcher_client):
    """Test execution error handling."""
    # Mock API failure
    mock_request_with_retry.side_effect = httpx.HTTPError("API Error")

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


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_track_child_pipeline_execution_success(
    mock_request_with_retry, watcher_client
):
    """Test successful child pipeline execution tracking."""
    # Mock API responses
    mock_start_response = Mock()
    mock_start_response.json.return_value = {"id": 456}
    mock_end_response = Mock()
    mock_end_response.json.return_value = {"status": "success"}

    mock_request_with_retry.side_effect = [mock_start_response, mock_end_response]

    # Test function
    def child_function(watcher_context: WatcherContext, data):
        assert watcher_context.execution_id == 456
        assert watcher_context.pipeline_id == 789
        assert watcher_context.watermark == "2024-01-01"
        assert watcher_context.next_watermark == "2024-01-02"
        return ETLResult(completed_successfully=True, total_rows=100, inserts=50)

    # Call the method
    result = watcher_client.track_child_pipeline_execution(
        pipeline_id=789,
        active=True,
        parent_execution_id=123,
        func=child_function,
        data="test_data",
        watermark="2024-01-01",
        next_watermark="2024-01-02",
    )

    # Verify API calls
    assert mock_request_with_retry.call_count == 2

    # Check start execution call
    start_call = mock_request_with_retry.call_args_list[0]
    assert start_call[0][0] == "POST"
    assert start_call[0][1] == "/start_pipeline_execution"
    start_payload = start_call[1]["json"]
    assert start_payload["pipeline_id"] == 789
    assert start_payload["parent_id"] == 123
    assert start_payload["watermark"] == "2024-01-01"
    assert start_payload["next_watermark"] == "2024-01-02"

    # Check end execution call
    end_call = mock_request_with_retry.call_args_list[1]
    assert end_call[0][0] == "POST"
    assert end_call[0][1] == "/end_pipeline_execution"
    end_payload = end_call[1]["json"]
    assert end_payload["id"] == 456
    assert end_payload["completed_successfully"] is True
    assert end_payload["total_rows"] == 100
    assert end_payload["inserts"] == 50

    # Verify result
    assert result.execution_id == 456
    assert result.result.completed_successfully is True
    assert result.result.total_rows == 100


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_track_child_pipeline_execution_without_watcher_context(
    mock_request_with_retry, watcher_client
):
    """Test child pipeline execution without WatcherContext parameter."""
    # Mock API responses
    mock_start_response = Mock()
    mock_start_response.json.return_value = {"id": 456}
    mock_end_response = Mock()
    mock_end_response.json.return_value = {"status": "success"}

    mock_request_with_retry.side_effect = [mock_start_response, mock_end_response]

    # Test function without WatcherContext
    def child_function(data):
        return ETLResult(completed_successfully=True, total_rows=200)

    # Call the method
    result = watcher_client.track_child_pipeline_execution(
        pipeline_id=789,
        active=True,
        parent_execution_id=123,
        func=child_function,
        data="test_data",
    )

    # Verify result
    assert result.execution_id == 456
    assert result.result.completed_successfully is True
    assert result.result.total_rows == 200


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_track_child_pipeline_execution_inactive_pipeline(
    mock_request_with_retry, watcher_client
):
    """Test child pipeline execution with inactive pipeline."""
    # Call the method with active=False
    result = watcher_client.track_child_pipeline_execution(
        pipeline_id=789,
        active=False,
        parent_execution_id=123,
        func=lambda: ETLResult(completed_successfully=True, total_rows=100),
    )

    # Should return None and not make API calls
    assert result is None
    assert mock_request_with_retry.call_count == 0


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_track_child_pipeline_execution_function_exception(
    mock_request_with_retry, watcher_client
):
    """Test child pipeline execution when function raises exception."""
    # Mock API responses
    mock_start_response = Mock()
    mock_start_response.json.return_value = {"id": 456}
    mock_end_response = Mock()
    mock_end_response.json.return_value = {"status": "success"}

    mock_request_with_retry.side_effect = [mock_start_response, mock_end_response]

    # Test function that raises exception
    def child_function():
        raise ValueError("Test error")

    # Should raise the exception
    with pytest.raises(ValueError, match="Test error"):
        watcher_client.track_child_pipeline_execution(
            pipeline_id=789, active=True, parent_execution_id=123, func=child_function
        )

    # Verify API calls were made
    assert mock_request_with_retry.call_count == 2

    # Check that end execution was called with failure
    end_call = mock_request_with_retry.call_args_list[1]
    end_payload = end_call[1]["json"]
    assert end_payload["id"] == 456
    assert end_payload["completed_successfully"] is False


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_track_child_pipeline_execution_invalid_return_type(
    mock_request_with_retry, watcher_client
):
    """Test child pipeline execution with invalid return type."""
    # Mock API responses
    mock_start_response = Mock()
    mock_start_response.json.return_value = {"id": 456}
    mock_end_response = Mock()
    mock_end_response.json.return_value = {"status": "success"}

    mock_request_with_retry.side_effect = [mock_start_response, mock_end_response]

    # Test function that returns invalid type
    def child_function():
        return "not an ETLResult"

    # Should raise ValueError
    with pytest.raises(ValueError, match="Function must return ETLResult"):
        watcher_client.track_child_pipeline_execution(
            pipeline_id=789, active=True, parent_execution_id=123, func=child_function
        )


@patch("watcher.client.ProductionHTTPClient.request_with_retry")
def test_track_child_pipeline_execution_with_execution_metadata(
    mock_request_with_retry, watcher_client
):
    """Test child pipeline execution with execution metadata."""
    # Mock API responses
    mock_start_response = Mock()
    mock_start_response.json.return_value = {"id": 456}
    mock_end_response = Mock()
    mock_end_response.json.return_value = {"status": "success"}

    mock_request_with_retry.side_effect = [mock_start_response, mock_end_response]

    # Test function
    def child_function():
        return ETLResult(
            completed_successfully=True,
            total_rows=100,
            execution_metadata={"ticker": "AAPL", "batch_id": "123"},
        )

    # Call the method
    result = watcher_client.track_child_pipeline_execution(
        pipeline_id=789, active=True, parent_execution_id=123, func=child_function
    )

    # Check end execution call includes metadata
    end_call = mock_request_with_retry.call_args_list[1]
    end_payload = end_call[1]["json"]
    assert end_payload["execution_metadata"] == {"ticker": "AAPL", "batch_id": "123"}

    # Verify result
    assert result.result.execution_metadata == {"ticker": "AAPL", "batch_id": "123"}
