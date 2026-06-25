from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from db import get_db
from models import Experiment, Event

router = APIRouter(prefix="/experiments", tags=["events"])

class EventIn(BaseModel):
    entity_id: str
    metric_name: str
    metric_value: float
    pre_period_value: Optional[float] = None

@router.post("/{exp_id}/events")
def record_event(exp_id: int, data: EventIn, db: Session = Depends(get_db)):
    exp = db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, "Эксперимент не найден")
    event = Event(
        experiment_id=exp_id,
        entity_id=data.entity_id,
        metric_name=data.metric_name,
        metric_value=data.metric_value,
        pre_period_value=data.pre_period_value
    )
    db.add(event)
    db.commit()
    return {"status": "ok", "experiment_id": exp_id, "entity_id": data.entity_id}
