"""
Статистические калькуляторы, не привязанные к конкретному эксперименту:
планирование выборки, оценка достигнутой мощности, поправки на
множественные сравнения.

Отдельный префикс /stats — эти расчёты нужны и до создания эксперимента
(сколько собирать), и после (что означает полученный результат).
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

from stats.power_analysis import sample_size_for_proportion, achieved_power
from stats.multiple_testing import correct
from stats.cuped import cuped_variance_reduction

router = APIRouter(prefix="/stats", tags=["stats-tools"])


@router.get("/sample-size")
def get_sample_size(
    baseline_rate: float = Query(gt=0.0, lt=1.0, description="Текущая конверсия, 0.10 = 10%"),
    mde: float = Query(description="Минимальный детектируемый эффект, 0.02 = +2пп"),
    alpha: float = Query(default=0.05, gt=0.0, lt=1.0),
    power: float = Query(default=0.8, gt=0.0, lt=1.0),
):
    """Сколько наблюдений на вариант нужно собрать до старта эксперимента."""
    try:
        return sample_size_for_proportion(baseline_rate, mde, alpha, power)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/achieved-power")
def get_achieved_power(
    n: int = Query(gt=0, description="Фактический размер выборки на вариант"),
    baseline_rate: float = Query(gt=0.0, lt=1.0),
    observed_effect: float = Query(description="Наблюдённый эффект в долях"),
    alpha: float = Query(default=0.05, gt=0.0, lt=1.0),
):
    """
    Какую мощность эксперимент имел фактически.

    Нужен, чтобы отличить «эффекта нет» от «выборки не хватило».
    """
    try:
        return achieved_power(n, baseline_rate, observed_effect, alpha)
    except ValueError as e:
        raise HTTPException(400, str(e))


class MultipleTestingRequest(BaseModel):
    p_values: List[float] = Field(min_length=1)
    method: str = Field(default="benjamini_hochberg")
    alpha: float = Field(default=0.05, gt=0.0, lt=1.0)
    labels: Optional[List[str]] = None


@router.post("/multiple-testing")
def apply_multiple_testing(data: MultipleTestingRequest):
    """
    Поправка на множественные сравнения.

    bonferroni контролирует вероятность хотя бы одной ошибки (FWER),
    benjamini_hochberg — ожидаемую долю ошибок среди находок (FDR)
    и находит больше реальных эффектов.
    """
    try:
        res = correct(data.p_values, method=data.method, alpha=data.alpha)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if data.labels:
        if len(data.labels) != len(data.p_values):
            raise HTTPException(400, "Длина labels не совпадает с длиной p_values")
        res["labels"] = data.labels
    return res


class CupedPreviewRequest(BaseModel):
    values: List[float] = Field(min_length=2)
    pre_values: List[float] = Field(min_length=2)


@router.post("/cuped-preview")
def preview_cuped(data: CupedPreviewRequest):
    """
    Насколько CUPED снизит дисперсию на этих данных.

    Полезно до эксперимента: если корреляция с предпериодом слабая,
    CUPED почти ничего не даст и усложнение не оправдано.
    """
    try:
        return cuped_variance_reduction(data.values, data.pre_values)
    except ValueError as e:
        raise HTTPException(400, str(e))
