"""
Power analysis: сколько наблюдений нужно до старта и что реально измерили после.

Расчёт до эксперимента — единственный способ отличить «эффекта нет»
от «выборки не хватило, чтобы его увидеть». Расчёт после — способ
честно описать незначимый результат, а не выдать его за доказательство
отсутствия эффекта.
"""
import numpy as np
from scipy import stats


def _validate_rate(value, name):
    if not (0.0 < value < 1.0):
        raise ValueError(f"{name} должен быть строго между 0 и 1, получено {value}")


def _validate_alpha_power(alpha, power):
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha должен быть строго между 0 и 1, получено {alpha}")
    if not (0.0 < power < 1.0):
        raise ValueError(f"power должен быть строго между 0 и 1, получено {power}")


def sample_size_for_proportion(baseline_rate: float, mde: float,
                               alpha=0.05, power=0.8) -> dict:
    """
    Размер выборки на вариант для обнаружения разности пропорций mde.

    baseline_rate: текущая конверсия (0.10 = 10%)
    mde: минимальный детектируемый эффект в абсолютных долях (0.02 = +2пп)
    """
    _validate_rate(baseline_rate, "baseline_rate")
    _validate_alpha_power(alpha, power)

    if mde == 0:
        raise ValueError(
            "MDE=0 требует бесконечной выборки: нельзя обнаружить нулевой эффект"
        )

    p1 = baseline_rate
    p2 = baseline_rate + mde
    if not (0.0 < p2 < 1.0):
        raise ValueError(
            f"baseline_rate + mde = {p2:.4f} выходит за границы (0, 1): "
            f"такая конверсия невозможна"
        )

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    p_pool = (p1 + p2) / 2

    n = (
        z_alpha * np.sqrt(2 * p_pool * (1 - p_pool))
        + z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2 / (p2 - p1) ** 2

    return {
        "baseline_rate": baseline_rate,
        "mde": mde,
        "alpha": alpha,
        "power": power,
        "sample_size_per_variant": int(np.ceil(n)),
        "sample_size_total": int(np.ceil(n)) * 2,
    }


def achieved_power(n: int, baseline_rate: float, observed_effect: float,
                   alpha=0.05) -> dict:
    """
    Мощность, фактически достигнутая при данном размере выборки и эффекте.

    Считается для величины эффекта, знак роли не играет.
    """
    if n <= 0:
        raise ValueError(f"n должен быть > 0, получено {n}")
    _validate_rate(baseline_rate, "baseline_rate")
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha должен быть строго между 0 и 1, получено {alpha}")

    p1 = baseline_rate
    p2 = baseline_rate + observed_effect
    if not (0.0 <= p2 <= 1.0):
        raise ValueError(
            f"baseline_rate + observed_effect = {p2:.4f} выходит за границы [0, 1]"
        )

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    p_pool = (p1 + p2) / 2
    se = np.sqrt(2 * p_pool * (1 - p_pool) / n)

    if se == 0:
        power = 0.0
    else:
        z_beta = abs(p2 - p1) / se - z_alpha
        power = float(stats.norm.cdf(z_beta))

    warnings = []
    if power < 0.5:
        warnings.append(
            f"Низкая мощность ({power:.2f}): незначимый результат при такой выборке "
            f"не является доказательством отсутствия эффекта."
        )

    return {
        "n_per_variant": n,
        "baseline_rate": baseline_rate,
        "observed_effect": observed_effect,
        "alpha": alpha,
        "achieved_power": round(power, 4),
        "warnings": warnings,
    }
