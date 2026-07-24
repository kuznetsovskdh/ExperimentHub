from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import Experiment, Assignment, Variant
from stats.randomization import assign_variant

router = APIRouter(prefix="/experiments", tags=["assignment"])

@router.get("/{exp_id}/assignment")
def get_assignment(exp_id: int, entity_id: str, db: Session = Depends(get_db)):
    exp = db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, "Эксперимент не найден")
    if exp.status != "active":
        raise HTTPException(400, "Эксперимент неактивен")

    existing = db.query(Assignment).filter_by(experiment_id=exp_id, entity_id=entity_id).first()
    if existing:
        variant = db.get(Variant, existing.variant_id)
        return {
            "experiment_id": exp_id,
            "entity_id": entity_id,
            "variant_id": existing.variant_id,
            "variant_name": variant.name if variant else None
        }

    variant_id = assign_variant(entity_id, exp_id, exp.variants)
    assignment = Assignment(experiment_id=exp_id, entity_id=entity_id, variant_id=variant_id)
    db.add(assignment)
    db.commit()
    variant = db.get(Variant, variant_id)
    return {
        "experiment_id": exp_id,
        "entity_id": entity_id,
        "variant_id": variant_id,
        "variant_name": variant.name if variant else None
    }
