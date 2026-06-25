import numpy as np

def bootstrap_ci(control, treatment, n_iterations=10000, alpha=0.05, seed=42):
    rng = np.random.default_rng(seed)
    ctrl = np.array(control)
    trt = np.array(treatment)
    observed_effect = np.mean(trt) - np.mean(ctrl)
    diffs = []
    for _ in range(n_iterations):
        s_ctrl = rng.choice(ctrl, size=len(ctrl), replace=True)
        s_trt = rng.choice(trt, size=len(trt), replace=True)
        diffs.append(np.mean(s_trt) - np.mean(s_ctrl))
    diffs = np.array(diffs)
    ci_lower = float(np.percentile(diffs, 100 * alpha / 2))
    ci_upper = float(np.percentile(diffs, 100 * (1 - alpha / 2)))
    p_value = float(np.mean(diffs <= 0) * 2) if observed_effect > 0 else float(np.mean(diffs >= 0) * 2)
    return {
        "method": "bootstrap",
        "effect_size": round(float(observed_effect), 6),
        "ci_lower": round(ci_lower, 6),
        "ci_upper": round(ci_upper, 6),
        "p_value": round(min(p_value, 1.0), 6),
        "significant": bool(ci_lower > 0 or ci_upper < 0)
    }
