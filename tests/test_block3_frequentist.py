"""
Блок 3. Классический AB-расчёт: корректность формул и крайние случаи.

Ключевой принцип блока — сверка не с "не упало", а с числом, которое
должно получиться по формуле (эталон: scipy/statsmodels).
"""
import math

import numpy as np
import pytest
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest

from stats.frequentist import z_test_proportions, t_test_continuous


def is_json_safe(d: dict) -> bool:
    """Ни одно числовое поле не должно быть nan/inf — иначе FastAPI отдаст 500."""
    for k, v in d.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return False
    return True


# --- 3.1 известный эффект ----------------------------------------------------

def test_3_1_detects_known_effect():
    """baseline 10% vs 12%, n=10000 → эффект ≈ +2пп, значимый, знак верный."""
    rng = np.random.default_rng(99)
    n = 10_000
    conv_c = int(rng.binomial(n, 0.10))
    conv_t = int(rng.binomial(n, 0.12))
    res = z_test_proportions(n, conv_c, n, conv_t)

    assert res["significant"], f"Эффект 2пп при n=10000 должен быть значим: {res}"
    assert res["effect_size"] > 0, "Знак эффекта должен быть положительным"
    assert abs(res["effect_size"] - 0.02) < 0.01, (
        f"Оценка эффекта {res['effect_size']:.4f} далеко от заданных 0.02"
    )
    assert res["ci_lower"] < res["effect_size"] < res["ci_upper"], "CI не покрывает оценку"


def test_3_1b_effect_sign_is_treatment_minus_control():
    """Если treatment хуже control, эффект должен быть отрицательным."""
    res = z_test_proportions(5000, 1000, 5000, 500)  # 20% vs 10%
    assert res["effect_size"] < 0, f"Ожидался отрицательный эффект: {res}"

    res_t = t_test_continuous([10.0] * 100 + [11.0] * 100, [1.0] * 100 + [2.0] * 100)
    assert res_t["effect_size"] < 0, f"Ожидался отрицательный эффект: {res_t}"


# --- 3.2 граница значимости --------------------------------------------------

def test_3_2_boundary_of_significance_is_consistent():
    """significant должен строго соответствовать p_value < alpha, без рассинхрона."""
    rng = np.random.default_rng(3)
    for _ in range(300):
        n = int(rng.integers(200, 3000))
        c = int(rng.binomial(n, 0.10))
        t = int(rng.binomial(n, 0.11))
        res = z_test_proportions(n, c, n, t, alpha=0.05)
        assert res["significant"] == (res["p_value"] < 0.05), (
            f"Рассинхрон significant и p_value: {res}"
        )


def test_3_2b_ci_agrees_with_pvalue_at_alpha():
    """
    При alpha=0.05 значимость по p-value и по доверительному интервалу
    (не накрывает ноль) должны совпадать — иначе CI посчитан по другой формуле.
    """
    rng = np.random.default_rng(5)
    mismatches = 0
    for _ in range(200):
        n = int(rng.integers(500, 5000))
        c = int(rng.binomial(n, 0.10))
        t = int(rng.binomial(n, 0.105))
        res = z_test_proportions(n, c, n, t, alpha=0.05)
        ci_excludes_zero = res["ci_lower"] > 0 or res["ci_upper"] < 0
        if ci_excludes_zero != res["significant"]:
            mismatches += 1
    # Небольшое расхождение возможно (pooled SE в тесте vs unpooled в CI),
    # но систематическое — признак ошибки.
    assert mismatches < 10, (
        f"CI и p-value расходятся в {mismatches}/200 случаях — "
        f"вероятно CI построен по формуле, не согласованной с тестом"
    )


def test_3_2c_alpha_is_respected_in_ci_width():
    """CI при alpha=0.01 должен быть ШИРЕ, чем при alpha=0.05."""
    r05 = z_test_proportions(5000, 500, 5000, 560, alpha=0.05)
    r01 = z_test_proportions(5000, 500, 5000, 560, alpha=0.01)
    w05 = r05["ci_upper"] - r05["ci_lower"]
    w01 = r01["ci_upper"] - r01["ci_lower"]
    assert w01 > w05, (
        f"CI не зависит от alpha (99%: {w01:.6f}, 95%: {w05:.6f}) — "
        f"скорее всего в формуле захардкожен множитель 1.96"
    )

    t05 = t_test_continuous([1, 2, 3, 4, 5] * 40, [2, 3, 4, 5, 6] * 40, alpha=0.05)
    t01 = t_test_continuous([1, 2, 3, 4, 5] * 40, [2, 3, 4, 5, 6] * 40, alpha=0.01)
    assert (t01["ci_upper"] - t01["ci_lower"]) > (t05["ci_upper"] - t05["ci_lower"]), (
        "t-test: CI не зависит от alpha — захардкожен 1.96"
    )


# --- 3.3 малый эффект на малой выборке --------------------------------------

def test_3_3_tiny_effect_small_sample_not_significant():
    """0.5пп разницы при n=100 не должно объявляться значимым."""
    res = z_test_proportions(100, 10, 100, 11)
    assert not res["significant"], f"Ложноположительный результат на малой выборке: {res}"


# --- 3.4/3.5 крайние случаи: нулевая дисперсия -------------------------------

def test_3_4_zero_conversions_both_groups():
    """Ни одной конверсии в обеих группах: не падать, не отдавать nan."""
    res = z_test_proportions(500, 0, 500, 0)
    assert is_json_safe(res), f"nan/inf в ответе при нулевых конверсиях: {res}"
    assert not res["significant"], "Различия нет — significant должен быть False"


def test_3_5_full_conversions_both_groups():
    """
    100% конверсия в обеих группах — реальный кейс из продакшена RusTest,
    который роняет /results с 500 (Out of range float values are not JSON compliant).
    """
    res = z_test_proportions(12, 12, 24, 24)
    assert is_json_safe(res), f"nan/inf в ответе при 100% конверсии: {res}"
    assert not res["significant"], "Различия нет — significant должен быть False"


def test_3_5b_zero_variance_continuous():
    """Все значения одинаковы в обеих группах → нулевая дисперсия в t-test."""
    res = t_test_continuous([5.0] * 50, [5.0] * 50)
    assert is_json_safe(res), f"nan/inf в t-test при нулевой дисперсии: {res}"
    assert not res["significant"]


def test_3_5c_zero_variance_but_different_means():
    """Константы, но разные: 5.0 vs 6.0. Дисперсия ноль, разница реальна."""
    res = t_test_continuous([5.0] * 50, [6.0] * 50)
    assert is_json_safe(res), f"nan/inf: {res}"
    assert res["effect_size"] == pytest.approx(1.0)


def test_3_4b_empty_groups_raise_clearly():
    """Пустая группа — явная ошибка, а не ZeroDivisionError/nan."""
    with pytest.raises(ValueError):
        z_test_proportions(0, 0, 100, 10)
    with pytest.raises(ValueError):
        t_test_continuous([], [1.0, 2.0])


def test_3_4c_single_observation_group():
    """n=1 в группе: дисперсия неопределена для t-test."""
    with pytest.raises(ValueError):
        t_test_continuous([5.0], [1.0, 2.0, 3.0])


def test_3_4d_conversions_exceed_sample_size():
    """conv > n физически невозможно — должно отвергаться."""
    with pytest.raises(ValueError):
        z_test_proportions(100, 150, 100, 10)


# --- 3.6 сверка с эталонной реализацией -------------------------------------

def test_3_6a_z_test_matches_statsmodels():
    """p-value z-теста должен совпадать с statsmodels.proportions_ztest (pooled)."""
    cases = [(1000, 100, 1000, 130), (5000, 500, 4800, 560), (300, 45, 700, 91)]
    for n_c, c_c, n_t, c_t in cases:
        ours = z_test_proportions(n_c, c_c, n_t, c_t)
        _, p_ref = proportions_ztest([c_t, c_c], [n_t, n_c])
        assert ours["p_value"] == pytest.approx(p_ref, abs=1e-5), (
            f"z-test расходится с эталоном на {(n_c, c_c, n_t, c_t)}: "
            f"наш={ours['p_value']}, statsmodels={p_ref}"
        )


def test_3_6b_t_test_matches_scipy():
    """p-value t-теста должен совпадать со scipy.stats.ttest_ind."""
    rng = np.random.default_rng(21)
    for _ in range(20):
        a = rng.normal(5, 2, 200).tolist()
        b = rng.normal(5.3, 2, 180).tolist()
        ours = t_test_continuous(a, b)
        _, p_ref = stats.ttest_ind(a, b, equal_var=False)
        assert ours["p_value"] == pytest.approx(p_ref, abs=1e-5), (
            f"t-test расходится со scipy: наш={ours['p_value']}, scipy={p_ref}"
        )


def test_3_6c_t_test_uses_welch_not_pooled():
    """
    При сильно разных дисперсиях и размерах групп Стьюдент и Уэлч расходятся.
    CI строится по несопряжённой (Welch) формуле, значит и p-value должен быть Welch,
    иначе p-value и CI описывают разные модели.
    """
    rng = np.random.default_rng(31)
    a = rng.normal(5, 1, 500).tolist()
    b = rng.normal(5.2, 6, 60).tolist()

    ours = t_test_continuous(a, b)
    _, p_welch = stats.ttest_ind(a, b, equal_var=False)
    _, p_student = stats.ttest_ind(a, b, equal_var=True)

    assert abs(ours["p_value"] - p_welch) < abs(ours["p_value"] - p_student) or \
        ours["p_value"] == pytest.approx(p_welch, abs=1e-5), (
        f"t-test использует Стьюдента (p={p_student:.6f}) при Welch-CI. "
        f"наш={ours['p_value']:.6f}, welch={p_welch:.6f}"
    )
