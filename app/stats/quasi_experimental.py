"""
Quasi-experimental методы: оценка эффекта там, где рандомизация невозможна.

Основной кейс — маркетинговая акция на конкретные SKU. Разделить товары
случайно нельзя (акция назначается по бизнес-логике), поэтому вместо AB
используется Difference-in-Differences: из изменения treatment-группы
вычитается изменение сопоставимой control-группы, что убирает общий
рыночный тренд и сезонность.

DiD верен ровно настолько, насколько верно допущение параллельных трендов:
без вмешательства обе группы менялись бы одинаково. Это допущение здесь
проверяется явно на предпериоде и выносится в ответ — молчаливое его
нарушение и есть главный способ получить красивую, но ложную оценку.
"""
import numpy as np
from scipy import stats


def _clean(values, name):
    if values is None:
        raise ValueError(f"{name}: не передано")
    arr = np.asarray([np.nan if v is None else v for v in values], dtype=float)
    if arr.size == 0:
        raise ValueError(
            f"{name}: пустой ряд. Для DiD нужны наблюдения и до, и после "
            f"вмешательства в обеих группах."
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name}: содержит None/nan/inf")
    return arr


def check_parallel_trends(treatment_before, control_before, alpha=0.05) -> dict:
    """
    Проверка допущения параллельных трендов на предпериоде.

    Сравниваются наклоны линейных трендов двух групп ДО вмешательства.
    Значимая разница наклонов означает, что группы расходились ещё до акции,
    и приписывать последующее расхождение акции нельзя.

    Важно: непрохождение теста — сильный сигнал против применимости DiD,
    а прохождение — не доказательство, а лишь отсутствие явного противоречия.
    """
    t = _clean(treatment_before, "treatment_before")
    c = _clean(control_before, "control_before")

    n = min(t.size, c.size)
    if n < 3:
        return {
            "testable": False,
            "violated": False,
            "warnings": [
                f"Точек до вмешательства слишком мало ({n}) для оценки тренда. "
                f"Допущение параллельных трендов не проверено — DiD применяется "
                f"под ответственность аналитика."
            ],
        }

    # Сравниваем наклоны на общем числе периодов (выравниваем по концу предпериода).
    t_tail, c_tail = t[-n:], c[-n:]
    x = np.arange(n, dtype=float)

    slope_t, _, _, _, se_t = stats.linregress(x, t_tail)
    slope_c, _, _, _, se_c = stats.linregress(x, c_tail)

    se_diff = np.sqrt(se_t ** 2 + se_c ** 2)
    diff = float(slope_t - slope_c)

    if se_diff == 0:
        p_value = 1.0 if diff == 0 else 0.0
        t_stat = 0.0
    else:
        t_stat = diff / se_diff
        df = max(2 * (n - 2), 1)
        p_value = float(2 * stats.t.sf(abs(t_stat), df))

    violated = bool(p_value < alpha)
    warnings = []
    if violated:
        warnings.append(
            f"Нарушено допущение параллельных трендов: до вмешательства treatment "
            f"менялся на {slope_t:.3f} за период, control на {slope_c:.3f} "
            f"(разница наклонов {diff:.3f}, p={p_value:.5f}). Группы расходились "
            f"ещё до акции — оценка DiD смещена и не может считаться чистым эффектом. "
            f"Подберите более сопоставимую control-группу."
        )

    return {
        "testable": True,
        "violated": violated,
        "slope_treatment": round(float(slope_t), 6),
        "slope_control": round(float(slope_c), 6),
        "slope_difference": round(diff, 6),
        "t_statistic": round(float(t_stat), 6),
        "p_value": round(float(p_value), 6),
        "n_pre_periods": int(n),
        "warnings": warnings,
    }


def difference_in_differences(
    treatment_before, treatment_after, control_before, control_after,
    alpha=0.05, n_iterations=5000, seed=42,
) -> dict:
    """
    DiD = (mean_trt_after - mean_trt_before) - (mean_ctrl_after - mean_ctrl_before)

    Неопределённость оценивается bootstrap-ресемплингом всех четырёх рядов,
    что не требует предположений о нормальности — уместно для выручки,
    у которой распределение скошено.
    """
    trt_b = _clean(treatment_before, "treatment_before")
    trt_a = _clean(treatment_after, "treatment_after")
    ctrl_b = _clean(control_before, "control_before")
    ctrl_a = _clean(control_after, "control_after")

    if n_iterations < 100:
        raise ValueError("n_iterations должно быть не меньше 100")

    mean_trt_before = float(np.mean(trt_b))
    mean_trt_after = float(np.mean(trt_a))
    mean_ctrl_before = float(np.mean(ctrl_b))
    mean_ctrl_after = float(np.mean(ctrl_a))

    delta_treatment = mean_trt_after - mean_trt_before
    delta_control = mean_ctrl_after - mean_ctrl_before
    did_effect = delta_treatment - delta_control

    rng = np.random.default_rng(seed)

    def resample_means(arr):
        idx = rng.integers(0, arr.size, size=(n_iterations, arr.size))
        return arr[idx].mean(axis=1)

    did_samples = (
        (resample_means(trt_a) - resample_means(trt_b))
        - (resample_means(ctrl_a) - resample_means(ctrl_b))
    )

    ci_lower = float(np.percentile(did_samples, 100 * alpha / 2))
    ci_upper = float(np.percentile(did_samples, 100 * (1 - alpha / 2)))

    if did_effect >= 0:
        tail = float(np.mean(did_samples <= 0))
    else:
        tail = float(np.mean(did_samples >= 0))
    p_value = min(2 * max(tail, 1.0 / n_iterations), 1.0)

    parallel = check_parallel_trends(trt_b, ctrl_b, alpha=alpha)

    warnings = list(parallel["warnings"])
    if min(trt_b.size, trt_a.size, ctrl_b.size, ctrl_a.size) < 5:
        warnings.append(
            "Меньше 5 наблюдений в одном из периодов — оценка крайне неустойчива."
        )
    if not parallel["testable"]:
        warnings.append(
            "Допущение параллельных трендов не проверялось автоматически: "
            "ответственность за сопоставимость control-группы на аналитике."
        )

    relative = None
    if mean_trt_before != 0:
        relative = round(did_effect / abs(mean_trt_before) * 100, 2)

    return {
        "method": "difference_in_differences",
        "mean_treatment_before": round(mean_trt_before, 4),
        "mean_treatment_after": round(mean_trt_after, 4),
        "mean_control_before": round(mean_ctrl_before, 4),
        "mean_control_after": round(mean_ctrl_after, 4),
        "delta_treatment": round(delta_treatment, 4),
        "delta_control": round(delta_control, 4),
        "did_effect": round(did_effect, 4),
        "did_effect_pct_of_baseline": relative,
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "alpha": alpha,
        "p_value": round(p_value, 6),
        "significant": bool(ci_lower > 0 or ci_upper < 0),
        "n_iterations": n_iterations,
        "parallel_trends": parallel,
        "warnings": warnings,
    }


def did_from_series(treatment: dict, control: dict, alpha=0.05,
                    n_iterations=5000, seed=42) -> dict:
    """
    DiD на панели сущностей (SKU → ряды до/после).

    treatment/control: {entity_id: {"pre": [...], "post": [...]}}

    Сущности без предпериода исключаются: товар, появившийся вместе с акцией,
    физически не имеет базы для сравнения, и его включение подменяет эффект
    акции эффектом ввода нового товара.
    """
    excluded, warnings = [], []

    def flatten(group, label):
        pre_all, post_all, pre_series = [], [], []
        for entity_id, series in group.items():
            pre = [v for v in series.get("pre", []) if v is not None]
            post = [v for v in series.get("post", []) if v is not None]
            if not pre:
                excluded.append(entity_id)
                continue
            if not post:
                excluded.append(entity_id)
                continue
            pre_all.extend(pre)
            post_all.extend(post)
            pre_series.append(pre)
        return pre_all, post_all, pre_series

    t_pre, t_post, t_pre_series = flatten(treatment, "treatment")
    c_pre, c_post, c_pre_series = flatten(control, "control")

    if excluded:
        warnings.append(
            f"Исключено сущностей без полного периода до/после: {len(excluded)} "
            f"({', '.join(map(str, excluded[:10]))}"
            f"{'...' if len(excluded) > 10 else ''}). "
            f"Для них DiD неприменим — нет базы сравнения."
        )

    if not t_pre or not t_post:
        raise ValueError(
            "После исключения сущностей без предпериода в treatment-группе "
            "не осталось данных для DiD"
        )
    if not c_pre or not c_post:
        raise ValueError("В control-группе нет данных для DiD")

    # Для проверки трендов используем среднюю по группе динамику по периодам.
    def mean_by_period(series_list):
        if not series_list:
            return []
        length = min(len(s) for s in series_list)
        if length == 0:
            return []
        return [
            float(np.mean([s[-length + i] for s in series_list]))
            for i in range(length)
        ]

    res = difference_in_differences(
        t_pre, t_post, c_pre, c_post,
        alpha=alpha, n_iterations=n_iterations, seed=seed,
    )

    trend_check = check_parallel_trends(
        mean_by_period(t_pre_series), mean_by_period(c_pre_series), alpha=alpha
    ) if mean_by_period(t_pre_series) and mean_by_period(c_pre_series) else res["parallel_trends"]

    res["parallel_trends"] = trend_check
    res["warnings"] = list(dict.fromkeys(warnings + trend_check["warnings"]))
    res["excluded_entities"] = excluded
    res["n_treatment_entities"] = len(treatment) - sum(
        1 for e in excluded if e in treatment
    )
    res["n_control_entities"] = len(control) - sum(
        1 for e in excluded if e in control
    )
    return res
