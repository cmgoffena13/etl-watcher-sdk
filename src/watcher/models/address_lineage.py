from typing import List, Optional

from pydantic import BaseModel, Field


class Address(BaseModel):
    name: str = Field(max_length=150, min_length=1)
    address_type_name: str = Field(max_length=150, min_length=1)
    address_type_group_name: str = Field(max_length=150, min_length=1)
    database_name: Optional[str] = Field(None, max_length=50)
    schema_name: Optional[str] = Field(None, max_length=50)
    table_name: Optional[str] = Field(None, max_length=50)
    primary_key: Optional[str] = Field(None, max_length=50)
    address_metadata: Optional[dict] = None


class AddressLineage(BaseModel):
    source_addresses: List[Address]
    target_addresses: List[Address]


class _AddressLineagePostInput(AddressLineage):
    pipeline_id: int
