import functools
import random
import time
from typing import Callable, List, Optional, Type

import httpx


def retry_http(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    jitter: bool = True,
    retry_status_codes: Optional[List[int]] = None,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
):
    """
    Decorator to add retry logic to HTTP calls.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for exponential backoff delay (default: 1.0)
        jitter: Whether to add random jitter to prevent thundering herd (default: True)
        retry_status_codes: HTTP status codes to retry on (default: [500, 502, 503, 504])
        retry_exceptions: Exception types to retry on (default: [httpx.ConnectError, httpx.TimeoutException])
    """
    if retry_status_codes is None:
        retry_status_codes = [500, 502, 503, 504]

    if retry_exceptions is None:
        retry_exceptions = [httpx.ConnectError, httpx.TimeoutException]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    response = func(*args, **kwargs)

                    # Check if we should retry based on status code
                    if (
                        hasattr(response, "status_code")
                        and response.status_code in retry_status_codes
                    ):
                        if attempt < max_retries:
                            delay = backoff_factor * (2**attempt)
                            if jitter:
                                # Add small random jitter (0-100ms) to prevent thundering herd
                                jitter_amount = random.uniform(0, 0.1)  # 0-100ms
                                delay += jitter_amount
                            time.sleep(delay)
                            continue
                        else:
                            # Last attempt failed, raise the response
                            response.raise_for_status()

                    return response

                except Exception as e:
                    last_exception = e

                    # Check if we should retry based on exception type
                    if any(isinstance(e, exc_type) for exc_type in retry_exceptions):
                        if attempt < max_retries:
                            delay = backoff_factor * (2**attempt)
                            if jitter:
                                # Add small random jitter (0-100ms) to prevent thundering herd
                                jitter_amount = random.uniform(0, 0.1)  # 0-100ms
                                delay += jitter_amount
                            time.sleep(delay)
                            continue

                    # Don't retry for other exceptions or if we've exhausted retries
                    raise e

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
