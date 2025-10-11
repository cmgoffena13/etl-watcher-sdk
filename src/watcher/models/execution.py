from typing import Optional, Union

from pydantic import BaseModel, Field
from pydantic_extra_types.pendulum_dt import Date, DateTime


class ETLResult(BaseModel):
    completed_successfully: bool
    inserts: Optional[int] = Field(default=None, ge=0)
    updates: Optional[int] = Field(default=None, ge=0)
    soft_deletes: Optional[int] = Field(default=None, ge=0)
    total_rows: Optional[int] = Field(default=None, ge=0)
    execution_metadata: Optional[dict] = None


class _EndPipelineExecutionInput(BaseModel):
    id: int
    end_date: DateTime
    completed_successfully: bool
    inserts: Optional[int] = Field(default=None, ge=0)
    updates: Optional[int] = Field(default=None, ge=0)
    soft_deletes: Optional[int] = Field(default=None, ge=0)
    total_rows: Optional[int] = Field(default=None, ge=0)
    execution_metadata: Optional[dict] = None


class WatcherContext(BaseModel):
    execution_id: int
    pipeline_id: int
    watermark: Optional[Union[str, int, DateTime, Date]] = None
    next_watermark: Optional[Union[str, int, DateTime, Date]] = None


class ExecutionResult(BaseModel):
    execution_id: int
    result: ETLResult
