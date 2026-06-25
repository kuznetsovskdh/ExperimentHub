from scipy import stats

def check_srm(observed_counts: list[int], expected_pcts: list[float], alpha=0.05) -> dict:
    total = sum(observed_counts)
    expected = [total * p / 100 for p in expected_pcts]
    chi2, p_value = stats.chisquare(observed_counts, expected)
    return {
        "chi2": round(float(chi2), 6),
        "p_value": round(float(p_value), 6),
        "srm_detected": bool(p_value < alpha)
    }
