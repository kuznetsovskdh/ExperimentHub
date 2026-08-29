"""
Блок 5. Bootstrap.

Ценность bootstrap — в отказе от предположения о нормальности. Поэтому
проверяем и согласие с параметрикой там, где она верна, и расхождение там,
где она ломается (тяжёлые хвосты) — совпадение во втором случае означало бы,
что метод реализован неправильно.
"""
import numpy as np
import pytest

from stats.bootstrap import bootstrap_ci
from stats.frequentist import t_test_continuous


# --- 5.1 согласие с параметрикой на нормальных данных ------------------------

def test_5_1_agrees_with_ttest_on_normal_data():
    """На нормальных данных bootstrap-CI и t-CI должны быть близки."""
    rng = np.random.default_rng(42)
    ctrl = rng.normal(5, 2, 1000).tolist()
    trt = rng.normal(6, 2, 1000).tolist()

    t_res = t_test_continuous(ctrl, trt)
    b_res = bootstrap_ci(ctrl, trt)

    assert abs(t_res["ci_lower"] - b_res["ci_lower"]) < 0.1
    assert abs(t_res["ci_upper"] - b_res["ci_upper"]) < 0.1
    assert t_res["significant"] == b_res["significant"]


@pytest.mark.slow
def test_5_1b_bootstrap_ci_coverage():
    """
    Прямая проверка корректности: 95%-й интервал должен накрывать истинный
    эффект примерно в 95% повторных экспериментов.
    """
    rng = np.random.default_rng(11)
    true_effect = 1.0
    covered = 0
    sims = 300
    for _ in range(sims):
        ctrl = rng.normal(5, 2, 200)
        trt = rng.normal(5 + true_effect, 2, 200)
        res = bootstrap_ci(ctrl.tolist(), trt.tolist(), n_iterations=2000)
        if res["ci_lower"] <= true_effect <= res["ci_upper"]:
            covered += 1
    coverage = covered / sims
    assert abs(coverage - 0.95) < 0.04, (
        f"Фактическое покрытие 95%-го CI = {coverage:.3f}. "
        f"Отклонение означает ошибку в построении интервала."
    )


@pytest.mark.slow
def test_5_1c_bootstrap_false_positive_rate():
    """AA под bootstrap: доля ложных срабатываний ≈ alpha."""
    rng = np.random.default_rng(13)
    fp = 0
    sims = 400
    for _ in range(sims):
        a = rng.normal(5, 2, 200).tolist()
        b = rng.normal(5, 2, 200).tolist()
        if bootstrap_ci(a, b, n_iterations=2000)["significant"]:
            fp += 1
    fpr = fp / sims
    assert abs(fpr - 0.05) < 0.03, f"bootstrap FPR={fpr:.4f}, ожидалось ~0.05"


# --- 5.2 расхождение на тяжёлых хвостах -------------------------------------

def test_5_2_differs_from_ttest_on_heavy_tails():
    """
    Выручка с редкими крупными заказами (логнормаль) — случай, ради которого
    bootstrap и нужен. Интервалы обязаны заметно разойтись, причём
    bootstrap-интервал должен быть асимметричным.
    """
    rng = np.random.default_rng(7)
    ctrl = rng.lognormal(3, 1.6, 400).tolist()
    trt = rng.lognormal(3.1, 1.6, 400).tolist()

    t_res = t_test_continuous(ctrl, trt)
    b_res = bootstrap_ci(ctrl, trt)

    effect = b_res["effect_size"]
    left = effect - b_res["ci_lower"]
    right = b_res["ci_upper"] - effect
    asymmetry = abs(left - right) / max(left, right)

    assert asymmetry > 0.02, (
        f"Bootstrap-интервал симметричен на скошенных данных (асимметрия "
        f"{asymmetry:.4f}) — это признак того, что он повторяет параметрическую "
        f"формулу вместо перцентилей. t-CI=[{t_res['ci_lower']}, {t_res['ci_upper']}], "
        f"b-CI=[{b_res['ci_lower']}, {b_res['ci_upper']}]"
    )


# --- 5.3 сходимость по числу итераций ---------------------------------------

def test_5_3_stability_across_iteration_counts():
    """CI при 1000 и 10000 итерациях не должны драматически расходиться."""
    rng = np.random.default_rng(5)
    ctrl = rng.normal(5, 2, 500).tolist()
    trt = rng.normal(5.5, 2, 500).tolist()

    r1k = bootstrap_ci(ctrl, trt, n_iterations=1000, seed=1)
    r10k = bootstrap_ci(ctrl, trt, n_iterations=10_000, seed=1)

    width = r10k["ci_upper"] - r10k["ci_lower"]
    assert abs(r1k["ci_lower"] - r10k["ci_lower"]) < 0.15 * width
    assert abs(r1k["ci_upper"] - r10k["ci_upper"]) < 0.15 * width


def test_5_3b_convergence_improves_with_iterations():
    """Разброс между сидами должен падать с ростом числа итераций."""
    rng = np.random.default_rng(9)
    ctrl = rng.normal(5, 2, 400).tolist()
    trt = rng.normal(5.4, 2, 400).tolist()

    def spread(n_iter):
        lowers = [bootstrap_ci(ctrl, trt, n_iterations=n_iter, seed=s)["ci_lower"]
                  for s in range(5)]
        return max(lowers) - min(lowers)

    assert spread(5000) < spread(300), "Bootstrap не сходится с ростом числа итераций"


def test_5_3c_seed_makes_result_reproducible():
    """Один seed → идентичный результат."""
    ctrl = [1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 10
    trt = [2.0, 3, 4, 5, 6, 7, 8, 9, 10, 11] * 10
    assert bootstrap_ci(ctrl, trt, seed=99) == bootstrap_ci(ctrl, trt, seed=99)


# --- 5.4 малые выборки ------------------------------------------------------

def test_5_4_small_sample_is_flagged():
    """n=10: метод работает, но платформа должна предупредить о ненадёжности."""
    rng = np.random.default_rng(3)
    ctrl = rng.normal(5, 2, 10).tolist()
    trt = rng.normal(6, 2, 10).tolist()
    res = bootstrap_ci(ctrl, trt)
    assert res["warnings"], f"Нет предупреждения о малой выборке: {res}"
    assert res["ci_upper"] > res["ci_lower"]


def test_5_4b_empty_group_raises():
    with pytest.raises(ValueError):
        bootstrap_ci([], [1.0, 2.0, 3.0])


def test_5_4c_single_value_group():
    """n=1: bootstrap вырождается — ресемплинг даёт одно и то же значение."""
    with pytest.raises(ValueError):
        bootstrap_ci([5.0], [1.0, 2.0, 3.0])


# --- корректность p-value ----------------------------------------------------

def test_5_5_pvalue_never_zero():
    """
    Bootstrap-p-value не может быть строго нулевым: минимум ограничен
    числом итераций. Ноль в отчёте создаёт ложное впечатление
    бесконечной уверенности.
    """
    rng = np.random.default_rng(1)
    ctrl = rng.normal(0, 1, 300).tolist()
    trt = rng.normal(10, 1, 300).tolist()
    res = bootstrap_ci(ctrl, trt, n_iterations=1000)
    assert res["p_value"] > 0, f"p_value=0 при 1000 итераций: {res}"
    assert res["p_value"] <= 1.0


def test_5_5b_pvalue_and_ci_agree():
    """Значимость по CI и по p-value должны совпадать."""
    rng = np.random.default_rng(17)
    for _ in range(30):
        ctrl = rng.normal(5, 2, 150).tolist()
        trt = rng.normal(5.3, 2, 150).tolist()
        res = bootstrap_ci(ctrl, trt, n_iterations=2000)
        ci_sig = res["ci_lower"] > 0 or res["ci_upper"] < 0
        assert ci_sig == res["significant"], f"Рассинхрон CI и significant: {res}"


def test_5_6_no_effect_gives_high_pvalue():
    """Идентичные группы → p-value близок к 1."""
    vals = list(np.random.default_rng(2).normal(5, 2, 300))
    res = bootstrap_ci(vals, list(vals))
    assert res["p_value"] > 0.5, f"Идентичные группы дали p={res['p_value']}"
    assert not res["significant"]
