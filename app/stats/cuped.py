"""
CUPED (Controlled-experiment Using Pre-Existing Data).

Y_cuped = Y - theta * (X - mean(X)),  theta = cov(Y, X) / var(X)

Смысл: из метрики вычитается та часть, которую можно предсказать по
предэкспериментальному значению. Дисперсия падает примерно на rho^2,
среднее не меняется — поэтому оценка эффекта остаётся несмещённой,
а доверительный интервал сужается.

Критично: theta и mean(X) обязаны считаться на ОБЪЕДИНЁННОЙ выборке
эксперимента. Если считать их отдельно по control и treatment,
преобразование станет функцией от групповых средних и внесёт смещение
в оценку эффекта — то есть CUPED начнёт менять ответ, а не только его точность.
"""
import numpy as np


def _as_clean_array(values, name):
    arr = np.asarray(
        [np.nan if v is None else v for v in values], dtype=float
    )
    if arr.size == 0:
        raise ValueError(f"{name}: пустая выборка")
    if not np.all(np.isfinite(arr)):
        raise ValueError(
            f"{name}: содержит None/nan/inf. Для CUPED нужно предэкспериментальное "
            f"значение у каждой сущности — исключите такие наблюдения явно "
            f"или откажитесь от CUPED для этой метрики."
        )
    return arr


def compute_theta(values: list, pre_values: list) -> float:
    """theta = cov(Y, X) / var(X) на переданной (обычно объединённой) выборке."""
    Y = _as_clean_array(values, "values")
    X = _as_clean_array(pre_values, "pre_values")
    if Y.size != X.size:
        raise ValueError(
            f"Длины не совпадают: values={Y.size}, pre_values={X.size}"
        )
    if X.size < 2:
        raise ValueError("Для оценки theta нужно минимум 2 наблюдения")

    var_x = np.var(X, ddof=1)
    if var_x == 0:
        raise ValueError(
            "Нулевая дисперсия предэкспериментальной метрики: theta не определена. "
            "CUPED неприменим — pre_period_value одинаков у всех сущностей."
        )
    return float(np.cov(Y, X, ddof=1)[0, 1] / var_x)


def apply_cuped(values: list, pre_values: list, theta: float = None,
                pre_mean: float = None) -> list:
    """
    CUPED-преобразование.

    theta и pre_mean можно передать снаружи — именно так их прокидывает
    cuped_adjust_groups, чтобы обе группы корректировались одинаково.
    """
    Y = _as_clean_array(values, "values")
    X = _as_clean_array(pre_values, "pre_values")
    if Y.size != X.size:
        raise ValueError(f"Длины не совпадают: values={Y.size}, pre_values={X.size}")

    if theta is None:
        theta = compute_theta(values, pre_values)
    if pre_mean is None:
        pre_mean = float(np.mean(X))

    return (Y - theta * (X - pre_mean)).tolist()


def cuped_adjust_groups(control_values, control_pre, treatment_values, treatment_pre):
    """
    Корректирует обе группы эксперимента согласованно.

    theta и mean(X) оцениваются на объединённой выборке — это то, что
    сохраняет несмещённость оценки эффекта.
    """
    all_values = list(control_values) + list(treatment_values)
    all_pre = list(control_pre) + list(treatment_pre)

    theta = compute_theta(all_values, all_pre)
    pre_mean = float(np.mean(_as_clean_array(all_pre, "pre_values")))

    adj_control = apply_cuped(control_values, control_pre, theta, pre_mean)
    adj_treatment = apply_cuped(treatment_values, treatment_pre, theta, pre_mean)
    return adj_control, adj_treatment


def cuped_variance_reduction(values: list, pre_values: list) -> dict:
    """Сравнение дисперсии до и после коррекции — наглядная польза CUPED."""
    theta = compute_theta(values, pre_values)
    Y_cuped = apply_cuped(values, pre_values, theta)

    var_before = float(np.var(values, ddof=1))
    var_after = float(np.var(Y_cuped, ddof=1))
    if var_before == 0:
        raise ValueError("Нулевая дисперсия метрики — сравнивать нечего")

    correlation = float(np.corrcoef(
        _as_clean_array(values, "values"), _as_clean_array(pre_values, "pre_values")
    )[0, 1])

    return {
        "theta": round(theta, 6),
        "correlation": round(correlation, 6),
        "var_before": round(var_before, 6),
        "var_after": round(var_after, 6),
        "reduction_pct": round((1 - var_after / var_before) * 100, 2),
    }
