import inspect
import warnings
from contextlib import contextmanager
from typing import Optional, Union

import httpx
import pendulum
from pydantic_extra_types.pendulum_dt import Date, DateTime

from watcher.exceptions import WatcherNetworkError, handle_http_error
from watcher.models.address_lineage import _AddressLineagePostInput
from watcher.models.execution import (
    ETLResult,
    ExecutionResult,
    WatcherContext,
    _EndPipelineExecutionInput,
)
from watcher.models.pipeline import (
    PipelineConfig,
    SyncedPipelineConfig,
    _PipelineInput,
    _PipelineResponse,
    _PipelineWithResponse,
)
from watcher.utils import retry_http


class Watcher:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.Client(
            base_url=base_url,
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0,
            ),
            timeout=30.0,
        )

    def _make_request(self, method: str, endpoint: str, **kwargs):
        """Make an HTTP request with retry logic and proper error handling."""
        try:
            response = self._make_request_with_retry(method, endpoint, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            raise handle_http_error(e)
        except httpx.RequestError as e:
            raise WatcherNetworkError(f"Network error: {e}")

    @retry_http(max_retries=3, backoff_factor=1.0, jitter=True)
    def _make_request_with_retry(self, method: str, endpoint: str, **kwargs):
        """Make an HTTP request with retry logic (internal method)."""
        return self.client.request(method, endpoint, **kwargs)

    def sync_pipeline_config(self, config: PipelineConfig) -> SyncedPipelineConfig:
        """
        Sync a pipeline config to the Watcher framework.
        If the pipeline is not active, raise a warning.
        If the pipeline watermark is not set, use the default watermark.
        If the pipeline load_lineage is true, sync the address lineage.
        Return the pipeline config.
        """
        pipeline_input = _PipelineInput(
            **config.pipeline.model_dump(),
            next_watermark=config.next_watermark,
        )
        pipeline_response = self._make_request(
            "POST",
            "/pipeline",
            json=pipeline_input.model_dump(exclude_unset=True),
        )
        pipeline_endpoint_response = _PipelineResponse(**(pipeline_response.json()))
        if pipeline_endpoint_response.active is False:
            warnings.warn(
                f"Pipeline '{config.pipeline.name}' (ID: {pipeline_endpoint_response.id}) is not active. "
                f"Sync operations skipped. Check pipeline status in the Watcher framework."
            )
            return SyncedPipelineConfig(
                pipeline=_PipelineWithResponse(
                    **config.pipeline.model_dump(),
                    id=pipeline_endpoint_response.id,
                    active=False,
                ),
                address_lineage=config.address_lineage,
                watermark=None,
                default_watermark=config.default_watermark,
                next_watermark=config.next_watermark,
            )

        if pipeline_endpoint_response.watermark is None:
            watermark = config.default_watermark
        else:
            watermark = pipeline_endpoint_response.watermark

        if pipeline_endpoint_response.load_lineage:
            address_lineage_data = _AddressLineagePostInput(
                pipeline_id=pipeline_endpoint_response.id,
                **config.address_lineage.model_dump(exclude_unset=True),
            )

            self._make_request(
                "POST",
                "/address_lineage",
                json=address_lineage_data.model_dump(exclude_unset=True),
            )

        return SyncedPipelineConfig(
            pipeline=_PipelineWithResponse(
                **config.pipeline.model_dump(),
                id=pipeline_endpoint_response.id,
                active=True,
            ),
            address_lineage=config.address_lineage,
            default_watermark=config.default_watermark,
            next_watermark=config.next_watermark,
            watermark=watermark,
        )

    def track_pipeline_execution(
        self,
        pipeline_id: int,
        active: bool,
        parent_execution_id: Optional[int] = None,
        watermark: Optional[Union[str, int, DateTime, Date]] = None,
        next_watermark: Optional[Union[str, int, DateTime, Date]] = None,
    ):
        """
        Decorator to track pipeline execution.
        Start the pipeline execution, and end it when the function is done.

        The decorated function must return ETLResult or a model that inherits from ETLResult.
        The ETLResult.completed_successfully field determines if the execution succeeded or failed.

        Exception Handling:
        - Unexpected exceptions (not handled by your ETL function) are logged as failures and re-raised
        - ETL function logic failures should be handled by returning ETLResult(completed_successfully=False)
        - You can handle errors however you want - just set completed_successfully appropriately

        Example:
            @watcher.track_pipeline_execution(pipeline_id=123)
            def my_etl_pipeline(watcher_context: WatcherContext):
                try:
                    # Your ETL logic
                    result = do_etl_work()
                    if result.success:
                        return ETLResult(completed_successfully=True, inserts=100)
                    else:
                        return ETLResult(completed_successfully=False, execution_metadata={"error": result.error})
                except Exception as e:
                    # Handle unexpected errors
                    return ETLResult(completed_successfully=False, execution_metadata={"exception": str(e)})
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                if active is False:
                    warnings.warn(
                        f"Pipeline {pipeline_id} is not active - aborting execution"
                    )
                    return None

                start_execution = {
                    "pipeline_id": pipeline_id,
                    "start_date": pendulum.now("UTC").isoformat(),
                }
                if parent_execution_id is not None:
                    start_execution["parent_id"] = parent_execution_id
                if watermark is not None:
                    start_execution["watermark"] = watermark
                if next_watermark is not None:
                    start_execution["next_watermark"] = next_watermark

                start_response = self._make_request(
                    "POST",
                    "/start_pipeline_execution",
                    json=start_execution,
                )
                execution_id = start_response.json()["id"]

                try:
                    sig = inspect.signature(func)
                    if "watcher_context" in sig.parameters:
                        watcher_context = WatcherContext(
                            execution_id=execution_id,
                            pipeline_id=pipeline_id,
                            watermark=watermark,
                            next_watermark=next_watermark,
                        )
                        result = func(watcher_context, *args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                    # Validate result is ETLResult or inherits from it
                    if not isinstance(result, ETLResult):
                        raise ValueError(
                            f"Function must return ETLResult or a model that inherits from ETLResult. "
                            f"Got: {type(result).__name__}"
                        )

                    end_payload_data = {
                        "id": execution_id,
                        "end_date": pendulum.now("UTC"),
                        "completed_successfully": result.completed_successfully,
                    }

                    for field in ETLResult.model_fields:
                        if field == "completed_successfully":
                            continue  # Already handled above
                        value = getattr(result, field)
                        if value is not None:
                            end_payload_data[field] = value

                    end_payload = _EndPipelineExecutionInput(**end_payload_data)

                    self._make_request(
                        "POST",
                        "/end_pipeline_execution",
                        json=end_payload.model_dump(mode="json", exclude_unset=True),
                    )

                    return ExecutionResult(execution_id=execution_id, result=result)

                except Exception as e:
                    error_payload = _EndPipelineExecutionInput(
                        id=execution_id,
                        end_date=pendulum.now("UTC"),
                        completed_successfully=False,
                    )

                    self._make_request(
                        "POST",
                        "/end_pipeline_execution",
                        json=error_payload.model_dump(mode="json", exclude_unset=True),
                    )
                    raise e

            return wrapper

        return decorator

    def track_child_pipeline_execution(
        self,
        pipeline_id: int,
        active: bool,
        parent_execution_id: int,
        func,
        watermark: Optional[Union[str, int, DateTime, Date]] = None,
        next_watermark: Optional[Union[str, int, DateTime, Date]] = None,
        *args,
        **kwargs,
    ):
        """Track a child execution. Call a function and capture its ETLResult."""
        if active is False:
            warnings.warn(f"Pipeline {pipeline_id} is not active - aborting execution")
            return None

        start_execution = {
            "pipeline_id": pipeline_id,
            "parent_id": parent_execution_id,
            "start_date": pendulum.now("UTC").isoformat(),
        }
        if watermark is not None:
            start_execution["watermark"] = watermark
        if next_watermark is not None:
            start_execution["next_watermark"] = next_watermark

        start_response = self._make_request(
            "POST",
            "/start_pipeline_execution",
            json=start_execution,
        )
        execution_id = start_response.json()["id"]

        try:
            # Check if function expects WatcherContext (same as decorator)
            sig = inspect.signature(func)
            if "watcher_context" in sig.parameters:
                watcher_context = WatcherContext(
                    execution_id=execution_id,
                    pipeline_id=pipeline_id,
                    watermark=watermark,
                    next_watermark=next_watermark,
                )
                result = func(watcher_context, *args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Validate result is ETLResult or inherits from it
            if not isinstance(result, ETLResult):
                raise ValueError(
                    f"Function must return ETLResult or a model that inherits from ETLResult. "
                    f"Got: {type(result).__name__}"
                )

            # End execution with actual ETLResult data (same as decorator)
            end_payload_data = {
                "id": execution_id,
                "end_date": pendulum.now("UTC"),
                "completed_successfully": result.completed_successfully,
            }

            for field in ETLResult.model_fields:
                if field == "completed_successfully":
                    continue  # Already handled above
                value = getattr(result, field)
                if value is not None:
                    end_payload_data[field] = value

            end_payload = _EndPipelineExecutionInput(**end_payload_data)

            self._make_request(
                "POST",
                "/end_pipeline_execution",
                json=end_payload.model_dump(mode="json", exclude_unset=True),
            )

            return ExecutionResult(execution_id=execution_id, result=result)

        except Exception as e:
            # Failure - end execution (same as decorator)
            error_payload = _EndPipelineExecutionInput(
                id=execution_id,
                end_date=pendulum.now("UTC"),
                completed_successfully=False,
            )
            self._make_request(
                "POST",
                "/end_pipeline_execution",
                json=error_payload.model_dump(mode="json", exclude_unset=True),
            )
            raise e

    def trigger_timeliness_check(self, lookback_minutes: int):
        self._make_request(
            "POST", "/timeliness", json={"lookback_minutes": lookback_minutes}
        )

    def trigger_freshness_check(self):
        self._make_request("POST", "/freshness")

    def trigger_celery_queue_check(self):
        self._make_request("POST", "/celery/monitor-queue")
