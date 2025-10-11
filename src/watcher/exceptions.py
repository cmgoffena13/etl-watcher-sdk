from typing import Any, Dict, Optional

import httpx


class WatcherError(Exception):
    """Base exception for all Watcher SDK errors."""

    pass


class WatcherAPIError(WatcherError):
    """Error from the Watcher API with detailed context."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
        response_headers: Optional[Dict[str, str]] = None,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.response_headers = response_headers or {}
        self.error_code = error_code
        self.error_details = error_details or {}

    def __str__(self):
        base_msg = super().__str__()
        if self.status_code:
            base_msg += f" (HTTP {self.status_code})"
        if self.error_code:
            base_msg += f" [{self.error_code}]"
        if self.response_text and len(self.response_text) < 200:
            base_msg += f" - {self.response_text}"
        return base_msg


class WatcherNetworkError(WatcherError):
    """Network or connection error."""

    pass


def handle_http_error(e) -> WatcherAPIError:
    """Convert httpx.HTTPStatusError to WatcherAPIError with API details."""
    if not isinstance(e, httpx.HTTPStatusError):
        raise TypeError("Expected httpx.HTTPStatusError")

    try:
        # Try to parse error details from API response
        error_data = e.response.json()
        api_message = error_data.get("message", error_data.get("error", str(e)))
        error_code = error_data.get("code")
        error_details = error_data.get("details", {})
    except Exception:
        # Fallback to response text or generic message
        api_message = e.response.text or str(e)
        error_code = None
        error_details = {}

    return WatcherAPIError(
        message=api_message,
        status_code=e.response.status_code,
        response_text=e.response.text,
        response_headers=dict(e.response.headers),
        error_code=error_code,
        error_details=error_details,
    )
