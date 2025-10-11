import pytest

from watcher.models.address_lineage import Address, AddressLineage
from watcher.models.pipeline import Pipeline, PipelineConfig
from watcher.types import DatePartEnum


@pytest.fixture
def sample_pipeline():
    """Create a sample Pipeline for testing."""
    return Pipeline(
        name="test-pipeline",
        pipeline_type_name="data-transformation",
        default_watermark="2024-01-01",
        next_watermark="2024-01-02",
        pipeline_metadata={"version": "1.0"},
        freshness_number=30,
        freshness_datepart=DatePartEnum.MINUTE,
        timeliness_number=60,
        timeliness_datepart=DatePartEnum.MINUTE,
    )


@pytest.fixture
def sample_source_address():
    """Create a sample Address for testing."""
    return Address(
        name="source_db.source_schema.source_table",
        address_type_name="postgres",
        address_type_group_name="database",
    )


@pytest.fixture
def sample_target_address():
    """Create a sample Address for testing."""
    return Address(
        name="target_db.target_schema.target_table",
        address_type_name="snowflake",
        address_type_group_name="warehouse",
    )


@pytest.fixture
def sample_address_lineage(sample_source_address, sample_target_address):
    """Create a sample AddressLineage for testing."""
    return AddressLineage(
        source_addresses=[sample_source_address],
        target_addresses=[sample_target_address],
    )


@pytest.fixture
def sample_pipeline_config(sample_pipeline, sample_address_lineage):
    """Create a sample PipelineConfig for testing."""
    return PipelineConfig(
        pipeline=sample_pipeline, address_lineage=sample_address_lineage
    )


@pytest.fixture
def mock_api_responses():
    """Create mock API responses for testing."""
    return {
        "pipeline_success": {
            "id": 123,
            "active": True,
            "load_lineage": True,
            "watermark": "2024-01-01",
        },
        "pipeline_inactive": {
            "id": 123,
            "active": False,
            "load_lineage": True,
            "watermark": None,
        },
        "pipeline_no_lineage": {
            "id": 123,
            "active": True,
            "load_lineage": False,
            "watermark": "2024-01-01",
        },
        "execution_start": {"id": 456},
    }
