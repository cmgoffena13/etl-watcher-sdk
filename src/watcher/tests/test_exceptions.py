from unittest.mock import Mock, patch

import httpx
import pytest

from watcher import WatcherAPIError, WatcherNetworkError


def test_api_error_handling(watcher_client, sample_pipeline_config):
    """Test that API errors are properly converted to WatcherAPIError."""
    # Mock a 404 response with API error details
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = '{"error": "Pipeline not found", "message": "Pipeline with ID 123 does not exist", "code": "PIPELINE_NOT_FOUND"}'
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {
        "error": "Pipeline not found",
        "message": "Pipeline with ID 123 does not exist",
        "code": "PIPELINE_NOT_FOUND",
    }

    # Mock httpx.HTTPStatusError
    http_error = httpx.HTTPStatusError(
        "404 Not Found", request=Mock(), response=mock_response
    )

    with patch.object(
        watcher_client, "_make_request_with_retry", side_effect=http_error
    ):
        with pytest.raises(WatcherAPIError) as exc_info:
            watcher_client.sync_pipeline_config(sample_pipeline_config)

        # Verify the exception has the correct details
        assert exc_info.value.status_code == 404
        assert exc_info.value.error_code == "PIPELINE_NOT_FOUND"
        assert "Pipeline with ID 123 does not exist" in str(exc_info.value)


def test_network_error_handling(watcher_client, sample_pipeline_config):
    """Test that network errors are properly converted to WatcherNetworkError."""
    # Mock a network error
    network_error = httpx.ConnectError("Connection failed")

    with patch.object(
        watcher_client, "_make_request_with_retry", side_effect=network_error
    ):
        with pytest.raises(WatcherNetworkError) as exc_info:
            watcher_client.sync_pipeline_config(sample_pipeline_config)

        # Verify the exception message
        assert "Network error" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)


def test_api_error_without_json_response(watcher_client, sample_pipeline_config):
    """Test API error handling when response is not JSON."""
    # Mock a 500 response without JSON
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.json.side_effect = ValueError("Not JSON")

    # Mock httpx.HTTPStatusError
    http_error = httpx.HTTPStatusError(
        "500 Internal Server Error", request=Mock(), response=mock_response
    )

    with patch.object(
        watcher_client, "_make_request_with_retry", side_effect=http_error
    ):
        with pytest.raises(WatcherAPIError) as exc_info:
            watcher_client.sync_pipeline_config(sample_pipeline_config)

        # Verify the exception has the correct details
        assert exc_info.value.status_code == 500
        assert exc_info.value.response_text == "Internal Server Error"
        assert "Internal Server Error" in str(exc_info.value)


def test_watcher_api_error_str_representation():
    """Test WatcherAPIError string representation."""
    error = WatcherAPIError(
        message="Test error", status_code=404, error_code="NOT_FOUND"
    )

    error_str = str(error)
    assert "Test error" in error_str
    assert "HTTP 404" in error_str
    assert "[NOT_FOUND]" in error_str


def test_watcher_api_error_with_long_response_text():
    """Test WatcherAPIError with long response text (should be truncated)."""
    long_text = "x" * 300  # 300 characters
    error = WatcherAPIError(
        message="Test error", status_code=500, response_text=long_text
    )

    error_str = str(error)
    assert "Test error" in error_str
    assert "HTTP 500" in error_str
    # Long text should be truncated in string representation
    assert len(error_str) < 300
