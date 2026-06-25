from scipy import stats

def check_srm(observed_counts: list[int], expected_pcts: list[float], alpha=0.05) -> dict:
    """
    SRM-проверка: хи-квадрат на распределение пользователей по вариантам.
    observed_counts: [n_control, n_treatment, ...]
    expected_pcts: [50.0, 50.0, ...] — ожидаемые проценты
    """
    total = sum(observed_counts)
    expected = [total * p / 100 for p in expected_pcts]
    chi2, p_value = stats.chisquare(observed_counts, expected)
    return {
        "chi2": round(float(chi2), 6),
        "p_value": round(float(p_value), 6),
        "srm_detected": p_value < alpha
    }
