from typing import Optional, Union

from pydantic import BaseModel, Field
from pydantic_extra_types.pendulum_dt import Date, DateTime

from watcher.models.address_lineage import AddressLineage
from watcher.types import DatePartEnum


class _PipelineInput(BaseModel):
    name: str = Field(max_length=150, min_length=1)
    pipeline_type_name: str = Field(max_length=150, min_length=1)
    next_watermark: Optional[Union[str, int, DateTime, Date]] = None
    pipeline_metadata: Optional[dict] = None
    freshness_number: Optional[int] = Field(default=None, gt=0)
    freshness_datepart: Optional[DatePartEnum] = None
    timeliness_number: Optional[int] = Field(default=None, gt=0)
    timeliness_datepart: Optional[DatePartEnum] = None


class Pipeline(_PipelineInput):
    default_watermark: Optional[Union[str, int, DateTime, Date]] = None


class _PipelineResponse(BaseModel):
    id: int
    active: bool
    load_lineage: bool
    watermark: Optional[Union[str, int, DateTime, Date]] = None


class PipelineConfig(BaseModel):
    pipeline: Pipeline
    address_lineage: AddressLineage


class SyncedPipelineConfig(PipelineConfig):
    id: int
    watermark: Optional[Union[str, int, DateTime, Date]] = None
    active: bool
