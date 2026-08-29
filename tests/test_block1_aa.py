"""
Блок 1. AA-тест — проверка что платформа не находит эффект там, где его нет.

Это главный тест доверия к платформе: доля ложноположительных результатов
в серии прогонов должна соответствовать заявленному alpha.
"""
import numpy as np
import pytest

from stats.frequentist import z_test_proportions, t_test_continuous


def false_positive_rate_binary(n_sim, n_per_variant, base_rate, alpha, seed=42,
                               n_control=None, n_treatment=None):
    """Доля ложных срабатываний z-теста при полном отсутствии эффекта."""
    rng = np.random.default_rng(seed)
    n_c = n_control or n_per_variant
    n_t = n_treatment or n_per_variant
    fp = 0
    for _ in range(n_sim):
        conv_a = int(rng.binomial(n_c, base_rate))
        conv_b = int(rng.binomial(n_t, base_rate))
        res = z_test_proportions(n_c, conv_a, n_t, conv_b, alpha)
        if res["significant"]:
            fp += 1
    return fp / n_sim


def false_positive_rate_continuous(n_sim, n_per_variant, alpha, seed=42):
    """Доля ложных срабатываний t-теста при полном отсутствии эффекта."""
    rng = np.random.default_rng(seed)
    fp = 0
    for _ in range(n_sim):
        a = rng.normal(5, 2, n_per_variant).tolist()
        b = rng.normal(5, 2, n_per_variant).tolist()
        if t_test_continuous(a, b, alpha)["significant"]:
            fp += 1
    return fp / n_sim


# --- 1.1 базовый AA ----------------------------------------------------------

@pytest.mark.slow
def test_1_1_aa_false_positive_rate_matches_alpha():
    """1000 прогонов без эффекта → доля p<0.05 должна быть ≈5%."""
    fpr = false_positive_rate_binary(1000, 500, 0.10, 0.05)
    assert abs(fpr - 0.05) < 0.02, (
        f"FPR={fpr:.4f} не соответствует alpha=0.05. "
        f"Слишком высокий → тест находит несуществующие эффекты; "
        f"слишком низкий → тест переконсервативен и не найдёт реальный."
    )


# --- 1.2 AA по типам метрик отдельно ----------------------------------------

@pytest.mark.slow
def test_1_2a_aa_binary_metric():
    """z-test для пропорций: корректный уровень ошибки первого рода."""
    fpr = false_positive_rate_binary(2000, 1000, 0.20, 0.05, seed=7)
    assert abs(fpr - 0.05) < 0.015, f"z-test FPR={fpr:.4f}, ожидалось ~0.05"


@pytest.mark.slow
def test_1_2b_aa_continuous_metric():
    """t-test для непрерывных: корректный уровень ошибки первого рода."""
    fpr = false_positive_rate_continuous(2000, 300, 0.05, seed=7)
    assert abs(fpr - 0.05) < 0.015, f"t-test FPR={fpr:.4f}, ожидалось ~0.05"


@pytest.mark.slow
def test_1_2c_aa_holds_at_alpha_01():
    """При alpha=0.01 доля ложных срабатываний должна упасть до ~1%."""
    fpr = false_positive_rate_binary(2000, 1000, 0.15, 0.01, seed=11)
    assert abs(fpr - 0.01) < 0.008, (
        f"FPR={fpr:.4f} при alpha=0.01. Если FPR не реагирует на alpha — "
        f"параметр alpha не проброшен в расчёт significant/CI."
    )


# --- 1.3 несбалансированные группы ------------------------------------------

@pytest.mark.slow
def test_1_3_aa_unbalanced_groups():
    """60/40 split: уровень ошибки первого рода не должен ломаться."""
    fpr = false_positive_rate_binary(
        2000, None, 0.12, 0.05, seed=13, n_control=1200, n_treatment=800
    )
    assert abs(fpr - 0.05) < 0.015, f"FPR при 60/40 = {fpr:.4f}, ожидалось ~0.05"
