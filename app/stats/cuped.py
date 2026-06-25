import numpy as np

def apply_cuped(values: list[float], pre_values: list[float]) -> list[float]:
    """
    CUPED-преобразование: Y_cuped = Y - theta * (X - mean(X))
    values: метрика после эксперимента
    pre_values: та же метрика до эксперимента
    """
    Y = np.array(values)
    X = np.array(pre_values)
    theta = np.cov(Y, X, ddof=1)[0, 1] / np.var(X, ddof=1)
    Y_cuped = Y - theta * (X - np.mean(X))
    return Y_cuped.tolist()

def cuped_variance_reduction(values: list[float], pre_values: list[float]) -> dict:
    """Сравнение дисперсии до и после CUPED-коррекции."""
    Y_cuped = apply_cuped(values, pre_values)
    var_before = float(np.var(values, ddof=1))
    var_after = float(np.var(Y_cuped, ddof=1))
    reduction_pct = (1 - var_after / var_before) * 100
    return {
        "var_before": round(var_before, 6),
        "var_after": round(var_after, 6),
        "reduction_pct": round(reduction_pct, 2)
    }
