from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from db import get_db
from models import Experiment, Event, Assignment

router = APIRouter(prefix="/experiments", tags=["events"])


class EventIn(BaseModel):
    entity_id: str = Field(min_length=1, max_length=512)
    metric_name: str = Field(min_length=1, max_length=255)
    metric_value: float
    pre_period_value: Optional[float] = None
    # Ключ идемпотентности. Клиент передаёт стабильный ключ (например
    # "attempt-1234-completion"), и повторная отправка при сетевом retry
    # не задваивает метрику.
    event_key: Optional[str] = Field(default=None, max_length=255)


@router.post("/{exp_id}/events")
def record_event(exp_id: int, data: EventIn, db: Session = Depends(get_db)):
    exp = db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, "Эксперимент не найден")

    if exp.status == "stopped":
        # Событие после остановки — почти всегда «хвост» ещё не обновлённого
        # клиента. Принимать его молча значит незаметно дописывать данные
        # в уже посчитанный эксперимент.
        raise HTTPException(
            409,
            f"Эксперимент {exp_id} остановлен, новые события не принимаются. "
            f"Обновите клиент или перезапустите эксперимент."
        )

    if data.metric_value != data.metric_value or data.metric_value in (
        float("inf"), float("-inf")
    ):
        raise HTTPException(400, "metric_value должно быть конечным числом")

    assigned = db.query(Assignment).filter_by(
        experiment_id=exp_id, entity_id=data.entity_id
    ).first()

    event = Event(
        experiment_id=exp_id,
        entity_id=data.entity_id,
        metric_name=data.metric_name,
        metric_value=data.metric_value,
        pre_period_value=data.pre_period_value,
        event_key=data.event_key,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        # Сработал uq_event_key — событие с таким ключом уже принято.
        db.rollback()
        return {
            "status": "duplicate_ignored",
            "experiment_id": exp_id,
            "entity_id": data.entity_id,
            "event_key": data.event_key,
        }

    return {
        "status": "ok",
        "experiment_id": exp_id,
        "entity_id": data.entity_id,
        "event_id": event.id,
        # Событие от сущности без назначения принимается (клиент мог собрать
        # метрику до интеграции assignment), но в расчёт эффекта не попадёт:
        # непонятно, к какому варианту его отнести.
        "assigned": assigned is not None,
        "warnings": (
            [] if assigned else [
                f"Сущность {data.entity_id} не имеет назначения в эксперименте "
                f"{exp_id}: событие сохранено, но в расчёт результатов не войдёт."
            ]
        ),
    }
