import warnings
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

import pendulum

from watcher import ETLResult, Watcher, WatcherContext
from watcher.models.pipeline import PipelineConfig


class OrchestrationContext:
    """Base class for orchestration context information."""

    def __init__(
        self,
        orchestrator: str,
        run_id: Optional[str] = None,
        execution_date: Optional[Union[str, datetime]] = None,
        partition_key: Optional[str] = None,
        dag_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs,
    ):
        self.orchestrator = orchestrator
        self.run_id = run_id
        self.execution_date = execution_date
        self.partition_key = partition_key
        self.dag_id = dag_id
        self.task_id = task_id
        self.extra_metadata = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for metadata."""
        return {
            "orchestrator": self.orchestrator,
            "run_id": self.run_id,
            "execution_date": str(self.execution_date) if self.execution_date else None,
            "partition_key": self.partition_key,
            "dag_id": self.dag_id,
            "task_id": self.task_id,
            **self.extra_metadata,
        }


class OrchestratedETL:
    """
    Simplified ETL wrapper that abstracts away orchestration complexity.

    This class provides a clean interface for running ETL pipelines with
    the ETL Watcher SDK. All orchestration context and watermark management
    is handled automatically.

    Example:
        # Simple usage - works with any orchestration framework
        etl = OrchestratedETL("https://api.watcher.com", pipeline_config)
        result = etl.execute_etl(my_etl_function)
    """

    def __init__(self, watcher_url: str, pipeline_config: PipelineConfig):
        """
        Initialize the orchestrated ETL wrapper.

        Args:
            watcher_url: Base URL for the Watcher API
            pipeline_config: Pipeline configuration to sync
        """
        self.watcher = Watcher(watcher_url)
        self.pipeline_config = pipeline_config
        self._synced_config = None

    def _get_synced_config(self) -> Any:
        """Get or create synced pipeline configuration."""
        if self._synced_config is None:
            self._synced_config = self.watcher.sync_pipeline_config(
                self.pipeline_config
            )
        return self._synced_config

    def _detect_orchestration_context(self, context: Any) -> OrchestrationContext:
        """
        Detect orchestration context from various framework contexts.

        Args:
            context: Context object from orchestration framework

        Returns:
            OrchestrationContext with detected information
        """
        # Check if it's already an OrchestrationContext
        if isinstance(context, OrchestrationContext):
            return context

        # Check for Dagster context
        if hasattr(context, "run_id") and hasattr(context, "partition_key"):
            return OrchestrationContext(
                orchestrator="dagster",
                run_id=getattr(context, "run_id", None),
                partition_key=getattr(context, "partition_key", None),
                dag_id=getattr(context, "dag_id", None),
                task_id=getattr(context, "task_id", None),
            )

        # Check for Airflow context (dict-like)
        elif isinstance(context, dict):
            return OrchestrationContext(
                orchestrator="airflow",
                run_id=context.get("run_id"),
                execution_date=context.get("execution_date"),
                dag_id=context.get("dag_id"),
                task_id=context.get("task_id"),
            )

        # Check for Airflow context (object with attributes)
        elif hasattr(context, "dag_id") and hasattr(context, "task_id"):
            return OrchestrationContext(
                orchestrator="airflow",
                run_id=getattr(context, "run_id", None),
                execution_date=getattr(context, "execution_date", None),
                dag_id=getattr(context, "dag_id", None),
                task_id=getattr(context, "task_id", None),
            )

        # Unknown context
        else:
            warnings.warn(
                f"Unknown orchestration context type: {type(context)}. "
                "Using generic context."
            )
            return OrchestrationContext(
                orchestrator="unknown", run_id=str(id(context)) if context else None
            )

    def execute_etl(
        self,
        etl_function: Callable[..., ETLResult],
        orchestration_context: Optional[Any] = None,
        parent_execution_id: Optional[int] = None,
        **kwargs,
    ) -> ETLResult:
        """
        Execute ETL function with orchestration context and Watcher tracking.

        Args:
            etl_function: ETL function that returns ETLResult
            orchestration_context: Context from orchestration framework
            parent_execution_id: ID of parent execution for tracking relationships
            **kwargs: Additional arguments to pass to ETL function

        Returns:
            ETLResult from the ETL function execution

        Raises:
            ValueError: If ETL function doesn't return ETLResult
        """
        # Get synced configuration
        synced_config = self._get_synced_config()

        # Detect orchestration context
        orch_context = self._detect_orchestration_context(orchestration_context)

        # Create the tracked ETL function
        execution_kwargs = {
            "pipeline_id": synced_config.pipeline.id,
            "active": synced_config.pipeline.active,
        }

        if synced_config.watermark is not None:
            execution_kwargs["watermark"] = synced_config.watermark

        if synced_config.next_watermark is not None:
            execution_kwargs["next_watermark"] = synced_config.next_watermark

        if parent_execution_id is not None:
            execution_kwargs["parent_execution_id"] = parent_execution_id

        @self.watcher.track_pipeline_execution(**execution_kwargs)
        def tracked_etl(watcher_context: WatcherContext):
            if orchestration_context is not None:
                orch_metadata = orch_context.to_dict()

                # Merge with existing execution_metadata if any
                if hasattr(watcher_context, "execution_metadata"):
                    existing_metadata = watcher_context.execution_metadata or {}
                    orch_metadata.update(existing_metadata)

                # Add orchestration context to the ETL function call
                if "orchestration_context" in etl_function.__code__.co_varnames:
                    kwargs["orchestration_context"] = orch_context

                # Store orchestration metadata for later use
                kwargs["_orchestration_metadata"] = orch_metadata

            # Execute the ETL function
            result = etl_function(watcher_context, **kwargs)

            # Validate result
            if not isinstance(result, ETLResult):
                raise ValueError(
                    f"ETL function must return ETLResult or a model that inherits from ETLResult. "
                    f"Got: {type(result).__name__}"
                )

            # Add orchestration metadata to the result
            if orchestration_context is not None:
                orch_metadata = orch_context.to_dict()

                if result.execution_metadata:
                    result.execution_metadata.update(orch_metadata)
                else:
                    result.execution_metadata = orch_metadata

            return result

        return tracked_etl()

    def start_parent_execution(self) -> int:
        """
        Start a parent execution and return the execution ID.

        This method starts an execution but does NOT complete it automatically.
        The execution should be ended manually when all child executions are complete.

        Returns:
            int: The execution ID of the started parent execution
        """
        # Get synced configuration
        synced_config = self._get_synced_config()

        if not synced_config.pipeline.active:
            warnings.warn(
                f"Pipeline {synced_config.pipeline.id} is not active - aborting execution"
            )
            return None

        start_execution = {
            "pipeline_id": synced_config.pipeline.id,
            "start_date": pendulum.now("UTC").isoformat(),
        }

        # Add watermark information
        if synced_config.watermark is not None:
            start_execution["watermark"] = synced_config.watermark
        if synced_config.next_watermark is not None:
            start_execution["next_watermark"] = synced_config.next_watermark

        start_response = self.watcher._make_request(
            "POST",
            "/start_pipeline_execution",
            json=start_execution,
        )
        execution_id = start_response.json()["id"]

        return execution_id

    def end_parent_execution(self, execution_id: int, result: ETLResult) -> None:
        """
        End a parent execution with the given result.

        Args:
            execution_id: The execution ID to end
            result: The ETLResult to report for the parent execution
        """
        end_execution = {
            "id": execution_id,
            "end_date": pendulum.now("UTC").isoformat(),
            "completed_successfully": result.completed_successfully,
        }

        # Add ETL result metrics
        if result.inserts is not None:
            end_execution["inserts"] = result.inserts
        if result.updates is not None:
            end_execution["updates"] = result.updates
        if result.soft_deletes is not None:
            end_execution["soft_deletes"] = result.soft_deletes
        if result.total_rows is not None:
            end_execution["total_rows"] = result.total_rows

        if result.execution_metadata is not None:
            end_execution["execution_metadata"] = result.execution_metadata

        self.watcher._make_request(
            "POST",
            "/end_pipeline_execution",
            json=end_execution,
        )
