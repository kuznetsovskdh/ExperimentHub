"""
Quasi-experimental эндпоинты для сценариев без рандомизации.

Данные передаются готовыми рядами, а не через общий поток событий:
DiD оперирует агрегированными временными рядами (SKU × период), и заводить
по Event на каждую пару SKU-день значило бы хранить сотни тысяч строк ради
четырёх средних.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from stats.quasi_experimental import (
    difference_in_differences,
    did_from_series,
    check_parallel_trends,
)

router = APIRouter(prefix="/quasi", tags=["quasi-experimental"])


class DiDRequest(BaseModel):
    treatment_before: List[float] = Field(min_length=1)
    treatment_after: List[float] = Field(min_length=1)
    control_before: List[float] = Field(min_length=1)
    control_after: List[float] = Field(min_length=1)
    alpha: float = Field(default=0.05, gt=0.0, lt=1.0)
    n_iterations: int = Field(default=5000, ge=100, le=100_000)


@router.post("/did")
def run_did(data: DiDRequest):
    """
    Difference-in-Differences на четырёх рядах.

    Ответ включает проверку допущения параллельных трендов: если группы
    расходились ещё до вмешательства, оценка эффекта смещена, и об этом
    сказано явно в parallel_trends и warnings.
    """
    try:
        return difference_in_differences(
            data.treatment_before,
            data.treatment_after,
            data.control_before,
            data.control_after,
            alpha=data.alpha,
            n_iterations=data.n_iterations,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


class EntitySeries(BaseModel):
    pre: List[Optional[float]] = []
    post: List[Optional[float]] = []


class DiDPanelRequest(BaseModel):
    treatment: Dict[str, EntitySeries]
    control: Dict[str, EntitySeries]
    alpha: float = Field(default=0.05, gt=0.0, lt=1.0)
    n_iterations: int = Field(default=5000, ge=100, le=100_000)


@router.post("/did-panel")
def run_did_panel(data: DiDPanelRequest):
    """
    DiD на панели сущностей: {sku: {pre: [...], post: [...]}}.

    Сущности без предпериода (товар, введённый вместе с акцией) исключаются
    и перечисляются в excluded_entities — включать их значило бы выдать
    эффект ввода нового товара за эффект акции.
    """
    try:
        return did_from_series(
            {k: v.model_dump() for k, v in data.treatment.items()},
            {k: v.model_dump() for k, v in data.control.items()},
            alpha=data.alpha,
            n_iterations=data.n_iterations,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


class ParallelTrendsRequest(BaseModel):
    treatment_before: List[float] = Field(min_length=2)
    control_before: List[float] = Field(min_length=2)
    alpha: float = Field(default=0.05, gt=0.0, lt=1.0)


@router.post("/parallel-trends")
def run_parallel_trends(data: ParallelTrendsRequest):
    """
    Отдельная проверка допущения параллельных трендов на предпериоде —
    её стоит запускать до того, как выбрана control-группа.
    """
    try:
        return check_parallel_trends(
            data.treatment_before, data.control_before, alpha=data.alpha
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
