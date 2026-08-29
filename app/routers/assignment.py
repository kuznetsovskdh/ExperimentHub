from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from db import get_db
from models import Experiment, Assignment, Variant
from stats.randomization import assign_variant

router = APIRouter(prefix="/experiments", tags=["assignment"])


@router.get("/{exp_id}/assignment")
def get_assignment(
    exp_id: int,
    entity_id: str = Query(min_length=1, max_length=512),
    db: Session = Depends(get_db),
):
    exp = db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, "Эксперимент не найден")
    if exp.status != "active":
        raise HTTPException(400, f"Эксперимент неактивен (статус: {exp.status})")

    existing = db.query(Assignment).filter_by(
        experiment_id=exp_id, entity_id=entity_id
    ).first()
    if existing:
        # Сохранённое назначение имеет приоритет над пересчётом по хэшу:
        # если allocation_pct поменяли по ходу эксперимента, уже назначенная
        # сущность обязана видеть тот же вариант, иначе ломается и UX,
        # и сопоставимость групп.
        variant = db.get(Variant, existing.variant_id)
        return _response(exp_id, entity_id, existing.variant_id, variant, cached=True)

    try:
        variant_id = assign_variant(entity_id, exp_id, exp.variants)
    except ValueError as e:
        raise HTTPException(400, str(e))

    db.add(Assignment(experiment_id=exp_id, entity_id=entity_id, variant_id=variant_id))
    try:
        db.commit()
    except IntegrityError:
        # Гонка: параллельный запрос для той же сущности успел записать первым.
        # Уникальное ограничение отработало — читаем победившую запись.
        db.rollback()
        existing = db.query(Assignment).filter_by(
            experiment_id=exp_id, entity_id=entity_id
        ).first()
        if not existing:
            raise HTTPException(500, "Не удалось сохранить назначение")
        variant = db.get(Variant, existing.variant_id)
        return _response(exp_id, entity_id, existing.variant_id, variant, cached=True)

    variant = db.get(Variant, variant_id)
    return _response(exp_id, entity_id, variant_id, variant, cached=False)


def _response(exp_id, entity_id, variant_id, variant, cached):
    return {
        "experiment_id": exp_id,
        "entity_id": entity_id,
        "variant_id": variant_id,
        "variant_name": variant.name if variant else None,
        "cached": cached,
    }
