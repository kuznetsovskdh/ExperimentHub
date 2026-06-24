from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import Experiment, Variant
from schemas import ExperimentCreate, ExperimentOut

router = APIRouter(prefix="/experiments", tags=["experiments"])

@router.post("/", response_model=ExperimentOut)
def create_experiment(data: ExperimentCreate, db: Session = Depends(get_db)):
    total = sum(v.allocation_pct for v in data.variants)
    if abs(total - 100.0) > 0.01:
        raise HTTPException(400, f"allocation_pct должны суммироваться в 100, получено {total}")
    exp = Experiment(name=data.name, entity_type=data.entity_type)
    db.add(exp)
    db.flush()
    for v in data.variants:
        db.add(Variant(experiment_id=exp.id, name=v.name, allocation_pct=v.allocation_pct))
    db.commit()
    db.refresh(exp)
    return exp

@router.get("/{exp_id}", response_model=ExperimentOut)
def get_experiment(exp_id: int, db: Session = Depends(get_db)):
    exp = db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, "Эксперимент не найден")
    return exp
