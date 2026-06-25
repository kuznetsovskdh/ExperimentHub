from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db import get_db
from models import Experiment, Assignment, Event, Result
from stats.frequentist import z_test_proportions, t_test_continuous
from stats.cuped import apply_cuped
from stats.bootstrap import bootstrap_ci
from stats.srm_check import check_srm

router = APIRouter(prefix="/experiments", tags=["results"])

@router.get("/{exp_id}/results")
def get_results(
    exp_id: int,
    metric_name: str,
    method: str = Query(default="auto", enum=["auto", "z_test", "t_test", "bootstrap"]),
    use_cuped: bool = False,
    db: Session = Depends(get_db)
):
    exp = db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, "Эксперимент не найден")

    variants = sorted(exp.variants, key=lambda v: v.id)
    if len(variants) != 2:
        raise HTTPException(400, "Результаты поддерживаются только для 2 вариантов")

    v_control, v_treatment = variants[0], variants[1]

    # Назначения для SRM
    assignments = db.query(Assignment).filter_by(experiment_id=exp_id).all()
    counts = {v.id: 0 for v in variants}
    for a in assignments:
        if a.variant_id in counts:
            counts[a.variant_id] += 1
    srm = check_srm(
        [counts[v_control.id], counts[v_treatment.id]],
        [v_control.allocation_pct, v_treatment.allocation_pct]
    )

    # События
    def get_events(variant_id):
        entity_ids = {a.entity_id for a in assignments if a.variant_id == variant_id}
        return db.query(Event).filter(
            Event.experiment_id == exp_id,
            Event.metric_name == metric_name,
            Event.entity_id.in_(entity_ids)
        ).all()

    ctrl_events = get_events(v_control.id)
    trt_events = get_events(v_treatment.id)

    if not ctrl_events or not trt_events:
        raise HTTPException(400, "Недостаточно данных для расчёта")

    ctrl_vals = [e.metric_value for e in ctrl_events]
    trt_vals = [e.metric_value for e in trt_events]

    if use_cuped:
        ctrl_pre = [e.pre_period_value for e in ctrl_events if e.pre_period_value is not None]
        trt_pre = [e.pre_period_value for e in trt_events if e.pre_period_value is not None]
        if len(ctrl_pre) == len(ctrl_vals) and len(trt_pre) == len(trt_vals):
            ctrl_vals = apply_cuped(ctrl_vals, ctrl_pre)
            trt_vals = apply_cuped(trt_vals, trt_pre)

    # Определяем метод
    is_binary = all(v in (0.0, 1.0) for v in ctrl_vals + trt_vals)
    if method == "auto":
        method = "z_test" if is_binary else "t_test"

    if method == "z_test":
        stat = z_test_proportions(len(ctrl_vals), int(sum(ctrl_vals)), len(trt_vals), int(sum(trt_vals)))
    elif method == "t_test":
        stat = t_test_continuous(ctrl_vals, trt_vals)
    else:
        stat = bootstrap_ci(ctrl_vals, trt_vals)

    return {
        "experiment_id": exp_id,
        "metric_name": metric_name,
        "method": stat["method"],
        "n_control": len(ctrl_vals),
        "n_treatment": len(trt_vals),
        "effect_size": stat["effect_size"],
        "p_value": stat["p_value"],
        "ci_lower": stat["ci_lower"],
        "ci_upper": stat["ci_upper"],
        "significant": stat["significant"],
        "srm": srm
    }
