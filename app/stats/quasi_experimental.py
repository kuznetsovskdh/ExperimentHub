import numpy as np

def difference_in_differences(
    treatment_before: list[float],
    treatment_after: list[float],
    control_before: list[float],
    control_after: list[float]
) -> dict:
    """
    Difference-in-Differences (DiD) для оценки эффекта без рандомизации.
    
    treatment_before/after: метрики treatment-группы до и после акции
    control_before/after: метрики контрольной группы за те же периоды
    
    DiD = (mean_trt_after - mean_trt_before) - (mean_ctrl_after - mean_ctrl_before)
    """
    mean_trt_before = float(np.mean(treatment_before))
    mean_trt_after = float(np.mean(treatment_after))
    mean_ctrl_before = float(np.mean(control_before))
    mean_ctrl_after = float(np.mean(control_after))

    delta_treatment = mean_trt_after - mean_trt_before
    delta_control = mean_ctrl_after - mean_ctrl_before
    did_effect = delta_treatment - delta_control

    # SE через bootstrap
    rng = np.random.default_rng(42)
    n_iter = 5000
    did_samples = []
    trt_b = np.array(treatment_before)
    trt_a = np.array(treatment_after)
    ctrl_b = np.array(control_before)
    ctrl_a = np.array(control_after)

    for _ in range(n_iter):
        s_trt_b = np.mean(rng.choice(trt_b, len(trt_b), replace=True))
        s_trt_a = np.mean(rng.choice(trt_a, len(trt_a), replace=True))
        s_ctrl_b = np.mean(rng.choice(ctrl_b, len(ctrl_b), replace=True))
        s_ctrl_a = np.mean(rng.choice(ctrl_a, len(ctrl_a), replace=True))
        did_samples.append((s_trt_a - s_trt_b) - (s_ctrl_a - s_ctrl_b))

    did_samples = np.array(did_samples)
    ci_lower = float(np.percentile(did_samples, 2.5))
    ci_upper = float(np.percentile(did_samples, 97.5))
    p_value = float(np.mean(did_samples <= 0) * 2) if did_effect > 0 else float(np.mean(did_samples >= 0) * 2)

    return {
        "method": "difference_in_differences",
        "mean_treatment_before": round(mean_trt_before, 4),
        "mean_treatment_after": round(mean_trt_after, 4),
        "mean_control_before": round(mean_ctrl_before, 4),
        "mean_control_after": round(mean_ctrl_after, 4),
        "delta_treatment": round(delta_treatment, 4),
        "delta_control": round(delta_control, 4),
        "did_effect": round(did_effect, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "p_value": round(min(p_value, 1.0), 6),
        "significant": bool(ci_lower > 0 or ci_upper < 0)
    }
