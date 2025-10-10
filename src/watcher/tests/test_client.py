"""
Tests for the Watcher client functionality.
"""

from unittest.mock import Mock, patch

import httpx
import pytest

from watcher.client import Watcher
from watcher.models.address_lineage import AddressLineage, SourceAddress, TargetAddress
from watcher.models.execution import ETLMetrics, WatcherExecutionContext
from watcher.models.pipeline import Pipeline, PipelineConfig, SyncedPipelineConfig


@pytest.fixture
def watcher_client():
    """Create a Watcher client for testing."""
    return Watcher("https://api.watcher.example.com")


@pytest.fixture
def sample_pipeline_config():
    """Create a sample pipeline configuration for testing."""
    return PipelineConfig(
        pipeline=Pipeline(
            name="test-pipeline",
            pipeline_type_name="extraction",
            default_watermark="2024-01-01",
        ),
        address_lineage=AddressLineage(
            source_addresses=[
                SourceAddress(
                    name="source-db",
                    address_type_name="database",
                    address_type_group_name="rdbms",
                )
            ],
            target_addresses=[
                TargetAddress(
                    name="target-warehouse",
                    address_type_name="data-warehouse",
                    address_type_group_name="analytics",
                )
            ],
        ),
    )


def test_watcher_initialization():
    """Test Watcher client initialization."""
    watcher = Watcher("https://api.example.com")
    assert watcher.base_url == "https://api.example.com"
    assert isinstance(watcher.client, httpx.Client)


@patch("httpx.Client.post")
def test_sync_pipeline_config_success(
    mock_post, watcher_client, sample_pipeline_config
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

    mock_post.side_effect = [mock_pipeline_response, mock_lineage_response]

    result = watcher_client.sync_pipeline_config(sample_pipeline_config)

    assert isinstance(result, SyncedPipelineConfig)
    assert result.active is True
    assert result.watermark == "2024-01-01"
    assert mock_post.call_count == 2  # Pipeline + address lineage


@patch("httpx.Client.post")
def test_sync_pipeline_config_inactive(
    mock_post, watcher_client, sample_pipeline_config
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
    mock_post.return_value = mock_response

    result = watcher_client.sync_pipeline_config(sample_pipeline_config)

    assert isinstance(result, SyncedPipelineConfig)
    assert result.active is False
    assert result.watermark is None  # Inactive pipelines have no watermark
    assert mock_post.call_count == 1  # Only pipeline call, no lineage


@patch("httpx.Client.post")
def test_sync_pipeline_config_no_lineage(
    mock_post, watcher_client, sample_pipeline_config
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
    mock_post.return_value = mock_response

    result = watcher_client.sync_pipeline_config(sample_pipeline_config)

    assert isinstance(result, SyncedPipelineConfig)
    assert result.active is True
    assert mock_post.call_count == 1  # Only pipeline call


@patch("httpx.Client.post")
def test_track_pipeline_execution_decorator_without_context(mock_post, watcher_client):
    """Test execution decorator without watcher_context parameter."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_end = Mock()
    mock_end.raise_for_status.return_value = None

    mock_post.side_effect = [mock_start, mock_end]

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def simple_etl():
        return ETLMetrics(inserts=100, total_rows=100)

    # This should work without watcher_context parameter
    result = simple_etl()
    assert result is not None


@patch("httpx.Client.post")
def test_track_pipeline_execution_decorator_with_context(mock_post, watcher_client):
    """Test execution decorator with watcher_context parameter."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_end = Mock()
    mock_end.raise_for_status.return_value = None

    mock_post.side_effect = [mock_start, mock_end]

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def etl_with_context(watcher_context: WatcherExecutionContext):
        assert isinstance(watcher_context, WatcherExecutionContext)
        assert watcher_context.pipeline_id == 123
        return ETLMetrics(inserts=100, total_rows=100)

    # This should work with watcher_context parameter
    result = etl_with_context()
    assert result is not None


def test_track_pipeline_execution_inactive_pipeline(watcher_client):
    """Test execution decorator with inactive pipeline."""

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=False)
    def etl_inactive():
        return ETLMetrics(inserts=100, total_rows=100)

    # Should return None for inactive pipeline
    result = etl_inactive()
    assert result is None


@patch("httpx.Client.post")
def test_etl_metrics_validation(mock_post, watcher_client):
    """Test ETLMetrics validation in decorator."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_end = Mock()
    mock_end.raise_for_status.return_value = None

    mock_post.side_effect = [mock_start, mock_end]

    class CustomMetrics(ETLMetrics):
        custom_field: str = "test"

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def etl_with_custom_metrics():
        return CustomMetrics(inserts=100, custom_field="hello")

    # Should work with inherited ETLMetrics
    result = etl_with_custom_metrics()
    assert result is not None


@patch("httpx.Client.post")
def test_etl_metrics_validation_failure(mock_post, watcher_client):
    """Test ETLMetrics validation failure."""
    # Mock API responses
    mock_start = Mock()
    mock_start.json.return_value = {"id": 456}
    mock_start.raise_for_status.return_value = None

    mock_post.return_value = mock_start

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def etl_invalid_return():
        return {"inserts": 100}  # Not ETLMetrics

    # Should raise ValueError for invalid return type
    with pytest.raises(ValueError, match="Function must return ETLMetrics"):
        etl_invalid_return()


@patch("httpx.Client.post")
def test_execution_error_handling(mock_post, watcher_client):
    """Test execution error handling."""
    # Mock API failure
    mock_post.side_effect = httpx.HTTPError("API Error")

    @watcher_client.track_pipeline_execution(pipeline_id=123, active=True)
    def etl_with_error():
        return ETLMetrics(inserts=100)

    # Should propagate the HTTP error
    with pytest.raises(httpx.HTTPError):
        etl_with_error()


def test_execution_context_fields():
    """Test WatcherExecutionContext contains expected fields."""
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


def test_etl_metrics_fields():
    """Test ETLMetrics contains expected fields."""
    metrics = ETLMetrics(
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
                SourceAddress(
                    name="source-db",
                    address_type_name="database",
                    address_type_group_name="rdbms",
                )
            ],
            target_addresses=[
                TargetAddress(
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
