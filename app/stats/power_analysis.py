import numpy as np
from scipy import stats

def sample_size_for_proportion(baseline_rate: float, mde: float, 
                                alpha=0.05, power=0.8) -> dict:
    """
    Калькулятор размера выборки для пропорций.
    baseline_rate: текущая конверсия (например 0.10)
    mde: minimum detectable effect (например 0.02 = +2pp)
    """
    p1 = baseline_rate
    p2 = baseline_rate + mde
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    p_pool = (p1 + p2) / 2
    n = (z_alpha * np.sqrt(2 * p_pool * (1 - p_pool)) + 
         z_beta * np.sqrt(p1 * (1-p1) + p2 * (1-p2))) ** 2 / (p2 - p1) ** 2
    return {
        "baseline_rate": baseline_rate,
        "mde": mde,
        "alpha": alpha,
        "power": power,
        "sample_size_per_variant": int(np.ceil(n))
    }

def achieved_power(n: int, baseline_rate: float, observed_effect: float, 
                   alpha=0.05) -> dict:
    """
    Достигнутая мощность по фактическим данным эксперимента.
    """
    p1 = baseline_rate
    p2 = baseline_rate + observed_effect
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    p_pool = (p1 + p2) / 2
    se = np.sqrt(2 * p_pool * (1 - p_pool) / n)
    z_beta = abs(p2 - p1) / se - z_alpha
    power = float(stats.norm.cdf(z_beta))
    return {
        "n_per_variant": n,
        "observed_effect": observed_effect,
        "achieved_power": round(power, 4)
    }
