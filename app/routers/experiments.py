from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from db import get_db
from models import Experiment, Variant, Assignment
from schemas import ExperimentCreate, ExperimentOut, ExperimentDetail

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("/", response_model=ExperimentDetail)
def create_experiment(data: ExperimentCreate, db: Session = Depends(get_db)):
    if len(data.variants) < 2:
        raise HTTPException(400, "Нужно минимум 2 варианта")

    names = [v.name for v in data.variants]
    if len(set(names)) != len(names):
        raise HTTPException(400, "Имена вариантов должны быть уникальны")

    total = sum(v.allocation_pct for v in data.variants)
    if abs(total - 100.0) > 0.01:
        raise HTTPException(
            400, f"allocation_pct должны суммироваться в 100, получено {total}"
        )
    if any(v.allocation_pct <= 0 for v in data.variants):
        raise HTTPException(400, "allocation_pct каждого варианта должен быть > 0")

    exp = Experiment(name=data.name, entity_type=data.entity_type)
    db.add(exp)
    db.flush()
    for v in data.variants:
        db.add(Variant(experiment_id=exp.id, name=v.name, allocation_pct=v.allocation_pct))
    db.commit()
    db.refresh(exp)
    return _detail(exp)


@router.get("/", response_model=List[ExperimentOut])
def list_experiments(db: Session = Depends(get_db)):
    return db.query(Experiment).order_by(Experiment.id).all()


@router.get("/{exp_id}", response_model=ExperimentDetail)
def get_experiment(exp_id: int, db: Session = Depends(get_db)):
    exp = db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, "Эксперимент не найден")
    return _detail(exp)


@router.post("/{exp_id}/stop", response_model=ExperimentDetail)
def stop_experiment(exp_id: int, db: Session = Depends(get_db)):
    """
    Останавливает эксперимент: новые назначения и события больше не принимаются.
    Уже собранные данные остаются доступны для расчёта результатов.
    """
    exp = db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, "Эксперимент не найден")
    if exp.status == "stopped":
        raise HTTPException(409, f"Эксперимент {exp_id} уже остановлен")

    exp.status = "stopped"
    exp.stopped_at = datetime.utcnow()
    db.commit()
    db.refresh(exp)
    return _detail(exp)


@router.post("/{exp_id}/resume", response_model=ExperimentDetail)
def resume_experiment(exp_id: int, db: Session = Depends(get_db)):
    """
    Возобновляет остановленный эксперимент.

    Пауза в сборе данных сама по себе меняет состав выборки (аудитория
    в разные периоды разная), поэтому возобновление — осознанное действие,
    а не автоматическое следствие.
    """
    exp = db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, "Эксперимент не найден")
    if exp.status == "active":
        raise HTTPException(409, f"Эксперимент {exp_id} уже активен")

    exp.status = "active"
    exp.stopped_at = None
    db.commit()
    db.refresh(exp)
    return _detail(exp)


def _detail(exp: Experiment) -> dict:
    return {
        "id": exp.id,
        "name": exp.name,
        "entity_type": exp.entity_type,
        "status": exp.status,
        "created_at": exp.created_at,
        "stopped_at": exp.stopped_at,
        "variants": [
            {"id": v.id, "name": v.name, "allocation_pct": v.allocation_pct}
            for v in sorted(exp.variants, key=lambda v: v.id)
        ],
    }
