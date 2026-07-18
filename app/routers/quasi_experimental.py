from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db import get_db
from stats.quasi_experimental import difference_in_differences

router = APIRouter(prefix="/quasi", tags=["quasi-experimental"])

class DiDRequest(BaseModel):
    treatment_before: list[float]
    treatment_after: list[float]
    control_before: list[float]
    control_after: list[float]

@router.post("/did")
def run_did(data: DiDRequest, db: Session = Depends(get_db)):
    return difference_in_differences(
        data.treatment_before,
        data.treatment_after,
        data.control_before,
        data.control_after
    )
