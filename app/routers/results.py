"""
Единая точка расчёта результатов эксперимента.

Два решения здесь определяют корректность всей платформы:

1. Агрегация событий до уровня сущности. Клиент может прислать несколько
   событий по одной метрике для одного entity_id (повторные попытки, retry,
   несколько заказов). Статистические тесты предполагают независимые
   наблюдения, поэтому в расчёт идёт одно значение на сущность.

2. Восполнение знаменателя. Для конверсионных метрик клиент обычно шлёт
   событие только при успехе. Если считать долю по одним лишь пришедшим
   событиям, конверсия всегда равна 100%. Параметр fill_missing позволяет
   явно сказать: всякая назначенная сущность без события — это ноль.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from db import get_db
from models import Experiment, Assignment, Event, Result
from stats.frequentist import z_test_proportions, t_test_continuous
from stats.cuped import cuped_adjust_groups
from stats.bootstrap import bootstrap_ci
from stats.srm_check import check_srm

router = APIRouter(prefix="/experiments", tags=["results"])

AGGREGATIONS = ("last", "first", "max", "min", "sum", "mean", "count")


def _aggregate(values, how):
    if how == "last":
        return values[-1]
    if how == "first":
        return values[0]
    if how == "max":
        return max(values)
    if how == "min":
        return min(values)
    if how == "sum":
        return sum(values)
    if how == "mean":
        return sum(values) / len(values)
    if how == "count":
        return float(len(values))
    raise ValueError(f"Неизвестная агрегация: {how}")


@router.get("/{exp_id}/results")
def get_results(
    exp_id: int,
    metric_name: str,
    method: str = Query(default="auto", enum=["auto", "z_test", "t_test", "bootstrap"]),
    use_cuped: bool = False,
    aggregation: str = Query(
        default="last",
        enum=list(AGGREGATIONS),
        description="Как свести несколько событий одной сущности к одному наблюдению",
    ),
    fill_missing: Optional[float] = Query(
        default=None,
        description=(
            "Значение для назначенных сущностей без событий. Для конверсионных "
            "метрик обычно 0 — иначе знаменатель состоит только из тех, "
            "у кого метрика сработала, и конверсия всегда равна 100%."
        ),
    ),
    alpha: float = Query(default=0.05, gt=0.0, lt=1.0),
    persist: bool = Query(default=False, description="Сохранить расчёт в таблицу results"),
    db: Session = Depends(get_db),
):
    exp = db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, "Эксперимент не найден")

    variants = sorted(exp.variants, key=lambda v: v.id)
    if len(variants) != 2:
        raise HTTPException(
            400,
            f"Расчёт поддерживается только для 2 вариантов, у эксперимента {exp_id} "
            f"их {len(variants)}. Для нескольких вариантов сравнивайте попарно "
            f"и применяйте поправку через /stats/multiple-testing.",
        )
    v_control, v_treatment = variants[0], variants[1]

    assignments = db.query(Assignment).filter_by(experiment_id=exp_id).all()
    if not assignments:
        raise HTTPException(400, "В эксперименте нет ни одного назначения")

    entity_to_variant = {a.entity_id: a.variant_id for a in assignments}
    counts = {v.id: 0 for v in variants}
    for a in assignments:
        if a.variant_id in counts:
            counts[a.variant_id] += 1

    srm = check_srm(
        [counts[v_control.id], counts[v_treatment.id]],
        [v_control.allocation_pct, v_treatment.allocation_pct],
        alpha=alpha,
    )

    events = (
        db.query(Event)
        .filter(Event.experiment_id == exp_id, Event.metric_name == metric_name)
        .order_by(Event.occurred_at, Event.id)
        .all()
    )

    # Группируем события по сущности, отбрасывая те, что не имеют назначения:
    # такое событие невозможно отнести к варианту.
    per_entity, orphan_events = {}, 0
    for e in events:
        if e.entity_id not in entity_to_variant:
            orphan_events += 1
            continue
        per_entity.setdefault(e.entity_id, []).append(e)

    warnings = list(srm["warnings"])
    if orphan_events:
        warnings.append(
            f"{orphan_events} событий пришло от сущностей без назначения — "
            f"они исключены из расчёта."
        )

    multi = sum(1 for v in per_entity.values() if len(v) > 1)
    if multi:
        warnings.append(
            f"У {multi} сущностей несколько событий по метрике '{metric_name}'. "
            f"Применена агрегация '{aggregation}' — по одному наблюдению на сущность."
        )

    groups = {v_control.id: [], v_treatment.id: []}
    pre_groups = {v_control.id: [], v_treatment.id: []}

    for entity_id, evs in per_entity.items():
        vid = entity_to_variant[entity_id]
        if vid not in groups:
            continue
        groups[vid].append(_aggregate([e.metric_value for e in evs], aggregation))
        pres = [e.pre_period_value for e in evs if e.pre_period_value is not None]
        pre_groups[vid].append(_aggregate(pres, aggregation) if pres else None)

    n_with_events = {vid: len(vals) for vid, vals in groups.items()}

    if fill_missing is not None:
        for a in assignments:
            if a.variant_id in groups and a.entity_id not in per_entity:
                groups[a.variant_id].append(float(fill_missing))
                pre_groups[a.variant_id].append(None)
        warnings.append(
            f"Сущностям без событий присвоено значение {fill_missing}: "
            f"control +{counts[v_control.id] - n_with_events[v_control.id]}, "
            f"treatment +{counts[v_treatment.id] - n_with_events[v_treatment.id]}."
        )
    else:
        missing = (counts[v_control.id] - n_with_events[v_control.id]) + (
            counts[v_treatment.id] - n_with_events[v_treatment.id]
        )
        if missing:
            warnings.append(
                f"{missing} назначенных сущностей не имеют событий по метрике "
                f"'{metric_name}' и исключены из расчёта. Если метрика "
                f"конверсионная, это завышает её значение — передайте "
                f"fill_missing=0, чтобы учесть их как нули."
            )

    ctrl_vals = groups[v_control.id]
    trt_vals = groups[v_treatment.id]

    if len(ctrl_vals) < 2 or len(trt_vals) < 2:
        raise HTTPException(
            400,
            f"Недостаточно данных: control={len(ctrl_vals)}, "
            f"treatment={len(trt_vals)} наблюдений (нужно минимум по 2).",
        )

    cuped_info = None
    if use_cuped:
        ctrl_pre = pre_groups[v_control.id]
        trt_pre = pre_groups[v_treatment.id]
        if any(p is None for p in ctrl_pre) or any(p is None for p in trt_pre):
            warnings.append(
                "CUPED не применён: предэкспериментальное значение есть не у всех "
                "сущностей. Передавайте pre_period_value в каждом событии метрики."
            )
        else:
            try:
                ctrl_vals, trt_vals = cuped_adjust_groups(
                    ctrl_vals, ctrl_pre, trt_vals, trt_pre
                )
                cuped_info = {"applied": True}
            except ValueError as e:
                warnings.append(f"CUPED не применён: {e}")

    is_binary = all(v in (0.0, 1.0) for v in ctrl_vals + trt_vals)
    chosen = method
    if method == "auto":
        chosen = "z_test" if is_binary else "t_test"
    if chosen == "z_test" and not is_binary:
        raise HTTPException(
            400,
            "z_test применим только к бинарной метрике (значения 0/1). "
            "Используйте t_test или bootstrap.",
        )

    try:
        if chosen == "z_test":
            stat = z_test_proportions(
                len(ctrl_vals), int(sum(ctrl_vals)),
                len(trt_vals), int(sum(trt_vals)), alpha=alpha,
            )
        elif chosen == "t_test":
            stat = t_test_continuous(ctrl_vals, trt_vals, alpha=alpha)
        else:
            stat = bootstrap_ci(ctrl_vals, trt_vals, alpha=alpha)
    except ValueError as e:
        raise HTTPException(400, f"Расчёт невозможен: {e}")

    warnings.extend(stat.get("warnings", []))

    if srm["srm_detected"]:
        warnings.insert(
            0,
            "SRM обнаружен — результату ниже доверять нельзя до выяснения причины "
            "перекоса в распределении по вариантам.",
        )

    payload = {
        "experiment_id": exp_id,
        "experiment_status": exp.status,
        "metric_name": metric_name,
        "method": stat["method"],
        "aggregation": aggregation,
        "fill_missing": fill_missing,
        "control_variant": {"id": v_control.id, "name": v_control.name},
        "treatment_variant": {"id": v_treatment.id, "name": v_treatment.name},
        "n_control": len(ctrl_vals),
        "n_treatment": len(trt_vals),
        "n_assigned_control": counts[v_control.id],
        "n_assigned_treatment": counts[v_treatment.id],
        "mean_control": round(sum(ctrl_vals) / len(ctrl_vals), 6),
        "mean_treatment": round(sum(trt_vals) / len(trt_vals), 6),
        "effect_size": stat["effect_size"],
        "p_value": stat["p_value"],
        "ci_lower": stat["ci_lower"],
        "ci_upper": stat["ci_upper"],
        "alpha": alpha,
        "significant": stat["significant"],
        "cuped": cuped_info,
        "srm": srm,
        "warnings": warnings,
    }

    if persist:
        db.add(Result(
            experiment_id=exp_id,
            metric_name=metric_name,
            method=stat["method"],
            n_control=len(ctrl_vals),
            n_treatment=len(trt_vals),
            p_value=stat["p_value"],
            ci_lower=stat["ci_lower"],
            ci_upper=stat["ci_upper"],
            effect_size=stat["effect_size"],
        ))
        db.commit()
        payload["persisted"] = True

    return payload
