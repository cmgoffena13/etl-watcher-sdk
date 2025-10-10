from typing import List

from pydantic import BaseModel, Field


class SourceAddress(BaseModel):
    name: str = Field(max_length=150, min_length=1)
    address_type_name: str = Field(max_length=150, min_length=1)
    address_type_group_name: str = Field(max_length=150, min_length=1)


class TargetAddress(BaseModel):
    name: str = Field(max_length=150, min_length=1)
    address_type_name: str = Field(max_length=150, min_length=1)
    address_type_group_name: str = Field(max_length=150, min_length=1)


class AddressLineage(BaseModel):
    source_addresses: List[SourceAddress]
    target_addresses: List[TargetAddress]


class _AddressLineagePostInput(AddressLineage):
    pipeline_id: int
