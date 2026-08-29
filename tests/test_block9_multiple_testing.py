"""
Блок 9. Множественное тестирование.

Сначала воспроизводим саму проблему (9.1), затем проверяем, что каждая
поправка действительно делает то, что обещает, и что trade-off между
ними виден на смешанном сценарии (9.3).
"""
import numpy as np
import pytest

from stats.multiple_testing import bonferroni, benjamini_hochberg, correct
from stats.frequentist import z_test_proportions


def run_aa_batch(n_tests, rng, n=2000, rate=0.10):
    """Пачка независимых AA-тестов (эффекта нет нигде) → список p-value."""
    out = []
    for _ in range(n_tests):
        c = int(rng.binomial(n, rate))
        t = int(rng.binomial(n, rate))
        out.append(z_test_proportions(n, c, n, t)["p_value"])
    return out


# --- 9.1 воспроизведение проблемы -------------------------------------------

@pytest.mark.slow
def test_9_1_uncorrected_20_tests_produce_false_positives():
    """
    20 AA-тестов без поправки → в среднем ~1 ложноположительный.
    Это и есть проблема, ради которой нужны поправки.
    """
    rng = np.random.default_rng(42)
    total_fp = 0
    batches = 200
    for _ in range(batches):
        p_values = run_aa_batch(20, rng)
        total_fp += sum(1 for p in p_values if p < 0.05)
    avg_fp = total_fp / batches
    assert 0.7 < avg_fp < 1.4, (
        f"Среднее число ложных срабатываний на 20 тестов = {avg_fp:.2f}, "
        f"ожидалось ~1.0 (20 * 0.05)"
    )


@pytest.mark.slow
def test_9_1b_family_wise_error_without_correction():
    """Вероятность хотя бы одной ошибки на 20 тестах ≈ 64%, а не 5%."""
    rng = np.random.default_rng(7)
    batches = 300
    any_fp = sum(
        1 for _ in range(batches) if any(p < 0.05 for p in run_aa_batch(20, rng))
    )
    fwer = any_fp / batches
    assert fwer > 0.5, (
        f"FWER={fwer:.3f}. Ожидалось ~0.64 = 1-(1-0.05)^20 — "
        f"наглядная демонстрация проблемы множественных сравнений."
    )


# --- 9.2 Бонферрони ---------------------------------------------------------

@pytest.mark.slow
def test_9_2_bonferroni_controls_fwer():
    """С Бонферрони доля прогонов хотя бы с одной ошибкой падает до ~alpha."""
    rng = np.random.default_rng(11)
    batches = 300
    any_fp = 0
    for _ in range(batches):
        res = bonferroni(run_aa_batch(20, rng), alpha=0.05)
        if res["n_rejected"] > 0:
            any_fp += 1
    fwer = any_fp / batches
    assert fwer < 0.08, f"Бонферрони не удержал FWER: {fwer:.3f}, ожидалось <=0.05"


def test_9_2b_bonferroni_threshold_and_adjustment():
    """Порог alpha/m, скорректированные p — умножение на m с обрезкой по 1."""
    res = bonferroni([0.001, 0.01, 0.04, 0.5], alpha=0.05)
    assert res["threshold"] == pytest.approx(0.0125)
    assert res["adjusted_p_values"] == [0.004, 0.04, 0.16, 1.0]
    assert res["rejected"] == [True, True, False, False]


def test_9_2c_bonferroni_single_test_is_noop():
    """При одном сравнении поправка ничего не меняет."""
    res = bonferroni([0.03], alpha=0.05)
    assert res["adjusted_p_values"] == [0.03]
    assert res["rejected"] == [True]


# --- 9.3 Беньямини—Хохберг и сравнение с Бонферрони -------------------------

def test_9_3_bh_is_less_conservative_than_bonferroni():
    """
    Смешанный сценарий: часть эффектов реальна, часть нет.
    BH должен находить не меньше, чем Бонферрони.
    """
    p_values = [0.001, 0.008, 0.02, 0.03, 0.04, 0.2, 0.5, 0.7, 0.8, 0.9]
    bonf = bonferroni(p_values, alpha=0.05)
    bh = benjamini_hochberg(p_values, alpha=0.05)
    assert bh["n_rejected"] >= bonf["n_rejected"], (
        f"BH нашёл {bh['n_rejected']}, Бонферрони {bonf['n_rejected']} — "
        f"BH не может быть консервативнее"
    )
    assert bh["n_rejected"] > bonf["n_rejected"], (
        "На этом наборе BH обязан находить строго больше — иначе он "
        "реализован как Бонферрони"
    )


def test_9_3b_bh_adjusted_p_values_are_monotone():
    """q-values должны неубывать вместе с p-values."""
    p_values = [0.001, 0.008, 0.02, 0.03, 0.04, 0.2, 0.5, 0.7, 0.8, 0.9]
    bh = benjamini_hochberg(p_values)
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    q_in_order = [bh["adjusted_p_values"][i] for i in order]
    assert q_in_order == sorted(q_in_order), f"q-values немонотонны: {q_in_order}"


def test_9_3c_bh_matches_reference_implementation():
    """Сверка с statsmodels.stats.multitest.multipletests(method='fdr_bh')."""
    from statsmodels.stats.multitest import multipletests

    p_values = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.2, 0.5, 0.9]
    ours = benjamini_hochberg(p_values, alpha=0.05)
    rejected_ref, q_ref, _, _ = multipletests(p_values, alpha=0.05, method="fdr_bh")

    np.testing.assert_allclose(ours["adjusted_p_values"], q_ref, atol=1e-6)
    assert ours["rejected"] == list(rejected_ref)


def test_9_3d_bonferroni_matches_reference():
    from statsmodels.stats.multitest import multipletests

    p_values = [0.001, 0.008, 0.039, 0.2, 0.5]
    ours = bonferroni(p_values, alpha=0.05)
    _, p_ref, _, _ = multipletests(p_values, alpha=0.05, method="bonferroni")
    np.testing.assert_allclose(ours["adjusted_p_values"], p_ref, atol=1e-6)


@pytest.mark.slow
def test_9_3e_bh_controls_fdr_on_mixed_scenario():
    """
    10 реальных эффектов + 10 пустых. BH должен держать долю ложных
    среди находок около alpha и находить больше, чем Бонферрони.
    """
    rng = np.random.default_rng(2024)
    n = 4000
    bh_fd, bh_disc, bonf_disc = 0, 0, 0
    batches = 200
    for _ in range(batches):
        p_values, is_null = [], []
        for i in range(20):
            true_lift = 0.02 if i < 10 else 0.0
            c = int(rng.binomial(n, 0.10))
            t = int(rng.binomial(n, 0.10 + true_lift))
            p_values.append(z_test_proportions(n, c, n, t)["p_value"])
            is_null.append(true_lift == 0.0)

        bh = benjamini_hochberg(p_values, alpha=0.05)
        bonf = bonferroni(p_values, alpha=0.05)
        bh_disc += bh["n_rejected"]
        bonf_disc += bonf["n_rejected"]
        bh_fd += sum(1 for i, r in enumerate(bh["rejected"]) if r and is_null[i])

    fdr = bh_fd / max(bh_disc, 1)
    assert fdr < 0.08, f"BH не удержал FDR: {fdr:.3f}"
    assert bh_disc > bonf_disc, (
        f"BH нашёл {bh_disc}, Бонферрони {bonf_disc} — "
        f"BH должен находить больше реальных эффектов"
    )


# --- валидация --------------------------------------------------------------

def test_9_4_validation():
    with pytest.raises(ValueError):
        bonferroni([])
    with pytest.raises(ValueError):
        benjamini_hochberg([0.5, 1.5])
    with pytest.raises(ValueError):
        benjamini_hochberg([0.5, None])
    with pytest.raises(ValueError):
        correct([0.5], method="holm-bonferroni-typo")


def test_9_5_none_method_warns_about_inflated_error():
    """Отказ от поправки должен сопровождаться явным предупреждением."""
    res = correct([0.01] * 20, method="none")
    assert res["warnings"], "Нет предупреждения при 20 сравнениях без поправки"
    assert "64" in res["warnings"][0] or "63" in res["warnings"][0]
