from pydantic import BaseModel

class VariantIn(BaseModel):
    name: str
    allocation_pct: float

class ExperimentCreate(BaseModel):
    name: str
    entity_type: str
    variants: list[VariantIn]

class ExperimentOut(BaseModel):
    id: int
    name: str
    entity_type: str
    status: str
    model_config = {"from_attributes": True}
