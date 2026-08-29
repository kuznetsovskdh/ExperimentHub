from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class VariantIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    allocation_pct: float = Field(gt=0, le=100)


class VariantOut(BaseModel):
    id: int
    name: str
    allocation_pct: float
    model_config = {"from_attributes": True}


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    # Свободная строка: "user", "sku", "region". Платформа не знает домена
    # подключённого продукта — это и делает её продуктово-агностичной.
    entity_type: str = Field(min_length=1, max_length=64)
    variants: List[VariantIn]


class ExperimentOut(BaseModel):
    id: int
    name: str
    entity_type: str
    status: str
    created_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class ExperimentDetail(ExperimentOut):
    variants: List[VariantOut] = []
