import numpy as np
from scipy import stats

def z_test_proportions(n_control, conv_control, n_treatment, conv_treatment, alpha=0.05):
    p1 = conv_control / n_control
    p2 = conv_treatment / n_treatment
    p_pool = (conv_control + conv_treatment) / (n_control + n_treatment)
    se = np.sqrt(p_pool * (1 - p_pool) * (1/n_control + 1/n_treatment))
    z = (p2 - p1) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    effect_size = p2 - p1
    ci_lower = effect_size - 1.96 * np.sqrt(p1*(1-p1)/n_control + p2*(1-p2)/n_treatment)
    ci_upper = effect_size + 1.96 * np.sqrt(p1*(1-p1)/n_control + p2*(1-p2)/n_treatment)
    return {
        "method": "z_test",
        "p_value": round(float(p_value), 6),
        "effect_size": round(float(effect_size), 6),
        "ci_lower": round(float(ci_lower), 6),
        "ci_upper": round(float(ci_upper), 6),
        "significant": bool(p_value < alpha)
    }

def t_test_continuous(control_values, treatment_values, alpha=0.05):
    t, p_value = stats.ttest_ind(control_values, treatment_values)
    effect_size = np.mean(treatment_values) - np.mean(control_values)
    n1, n2 = len(control_values), len(treatment_values)
    se = np.sqrt(np.var(control_values, ddof=1)/n1 + np.var(treatment_values, ddof=1)/n2)
    ci_lower = effect_size - 1.96 * se
    ci_upper = effect_size + 1.96 * se
    return {
        "method": "t_test",
        "p_value": round(float(p_value), 6),
        "effect_size": round(float(effect_size), 6),
        "ci_lower": round(float(ci_lower), 6),
        "ci_upper": round(float(ci_upper), 6),
        "significant": bool(p_value < alpha)
    }
