"""
Bootstrap-резамплинг для доверительных интервалов.

Непараметрическая альтернатива t-тесту: не предполагает нормальности,
поэтому корректно работает на скошенных распределениях (выручка, чек,
время на задании), где параметрический интервал систематически врёт.
"""
import numpy as np

MIN_RECOMMENDED_N = 30


def bootstrap_ci(control, treatment, n_iterations=10_000, alpha=0.05, seed=42):
    """
    Перцентильный bootstrap разности средних.

    p-value считается как доля ресемплов, лежащих по другую сторону нуля
    относительно наблюдённого эффекта (двусторонний). Он ограничен снизу
    величиной 1/n_iterations: bootstrap не может доказать больше, чем
    позволяет число итераций, и сообщать p=0 было бы неверно.
    """
    ctrl = np.asarray(control, dtype=float)
    trt = np.asarray(treatment, dtype=float)

    if ctrl.size < 2 or trt.size < 2:
        raise ValueError(
            f"Для bootstrap нужно минимум 2 наблюдения в группе "
            f"(получено control={ctrl.size}, treatment={trt.size})"
        )
    if not np.all(np.isfinite(ctrl)) or not np.all(np.isfinite(trt)):
        raise ValueError("Входные данные содержат nan/inf")
    if n_iterations < 100:
        raise ValueError("n_iterations должно быть не меньше 100")

    rng = np.random.default_rng(seed)
    observed_effect = float(np.mean(trt) - np.mean(ctrl))

    # Векторный ресемплинг: (n_iterations, n) индексов за один проход.
    idx_c = rng.integers(0, ctrl.size, size=(n_iterations, ctrl.size))
    idx_t = rng.integers(0, trt.size, size=(n_iterations, trt.size))
    diffs = ctrl[idx_c].mean(axis=1)
    diffs = trt[idx_t].mean(axis=1) - diffs

    ci_lower = float(np.percentile(diffs, 100 * alpha / 2))
    ci_upper = float(np.percentile(diffs, 100 * (1 - alpha / 2)))

    # Доля ресемплов по «неправильную» сторону нуля, удвоенная (двусторонний).
    if observed_effect >= 0:
        tail = float(np.mean(diffs <= 0))
    else:
        tail = float(np.mean(diffs >= 0))
    p_value = min(2 * max(tail, 1.0 / n_iterations), 1.0)

    warnings = []
    if min(ctrl.size, trt.size) < MIN_RECOMMENDED_N:
        warnings.append(
            f"Малая выборка (min n={min(ctrl.size, trt.size)}): bootstrap "
            f"переоценивает точность, так как ресемплит из бедной эмпирической "
            f"функции распределения. Интервал считайте ориентировочным."
        )
    if p_value <= 2.0 / n_iterations:
        warnings.append(
            f"p-value уперся в разрешение метода (1/{n_iterations}). "
            f"Точное значение меньше — увеличьте n_iterations, если нужна цифра."
        )

    return {
        "method": "bootstrap",
        "n_iterations": n_iterations,
        "effect_size": round(observed_effect, 6),
        "ci_lower": round(ci_lower, 6),
        "ci_upper": round(ci_upper, 6),
        "alpha": alpha,
        "p_value": round(p_value, 6),
        "significant": bool(ci_lower > 0 or ci_upper < 0),
        "warnings": warnings,
    }
