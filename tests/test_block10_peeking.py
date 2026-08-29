"""
Блок 10. Peeking — подглядывание в промежуточные результаты.

Если смотреть на p-value каждый день и останавливаться на первом дне,
когда он опустился ниже 0.05, фактический уровень ошибки первого рода
многократно превышает заявленный. Платформа не реализует sequential
testing, поэтому её задача — измерить масштаб проблемы и честно
предупредить пользователя.
"""
import numpy as np
import pytest

from stats.frequentist import z_test_proportions
from stats.power_analysis import sample_size_for_proportion


def run_peeking_simulation(n_sim, days, daily_n, base_rate, alpha=0.05, seed=42):
    """
    Возвращает (доля ложных при подглядывании, доля ложных при честной остановке).
    Эффекта нет — любое «значимое» открытие ложное.
    """
    rng = np.random.default_rng(seed)
    peeking_fp = 0
    fixed_fp = 0

    for _ in range(n_sim):
        conv_c = conv_t = 0
        n_total = 0
        stopped_early = False

        for _ in range(days):
            conv_c += int(rng.binomial(daily_n, base_rate))
            conv_t += int(rng.binomial(daily_n, base_rate))
            n_total += daily_n
            if not stopped_early:
                res = z_test_proportions(n_total, conv_c, n_total, conv_t, alpha)
                if res["significant"]:
                    stopped_early = True

        if stopped_early:
            peeking_fp += 1
        final = z_test_proportions(n_total, conv_c, n_total, conv_t, alpha)
        if final["significant"]:
            fixed_fp += 1

    return peeking_fp / n_sim, fixed_fp / n_sim


@pytest.mark.slow
def test_10_1_peeking_inflates_false_positive_rate():
    """
    Ежедневное подглядывание в течение 30 дней должно заметно поднять долю
    ложных открытий по сравнению с одной проверкой в конце.
    """
    peek_fpr, fixed_fpr = run_peeking_simulation(
        n_sim=400, days=30, daily_n=100, base_rate=0.10
    )
    print(
        f"\nPeeking: 30 ежедневных проверок → FPR={peek_fpr:.3f}; "
        f"одна проверка в конце → FPR={fixed_fpr:.3f}"
    )

    assert abs(fixed_fpr - 0.05) < 0.03, (
        f"Честная остановка должна давать FPR≈0.05, получено {fixed_fpr:.3f}"
    )
    assert peek_fpr > 2 * fixed_fpr, (
        f"Подглядывание не увеличило FPR ({peek_fpr:.3f} против {fixed_fpr:.3f}) — "
        f"симуляция не воспроизводит проблему"
    )
    assert peek_fpr > 0.15, (
        f"FPR при подглядывании {peek_fpr:.3f}: ожидалось существенное превышение "
        f"заявленных 5%"
    )


@pytest.mark.slow
def test_10_2_peeking_severity_grows_with_frequency():
    """Чем чаще проверки, тем сильнее раздувается ошибка."""
    few, _ = run_peeking_simulation(300, days=5, daily_n=600, base_rate=0.10, seed=1)
    many, _ = run_peeking_simulation(300, days=30, daily_n=100, base_rate=0.10, seed=1)
    print(f"\n5 проверок → FPR={few:.3f}; 30 проверок → FPR={many:.3f}")
    assert many > few, (
        f"Более частое подглядывание должно давать больший FPR: "
        f"5 проверок {few:.3f}, 30 проверок {many:.3f}"
    )


def test_10_3_fixed_sample_size_is_computable_upfront():
    """
    Защита от peeking — заранее рассчитанный размер выборки.
    Проверяем, что платформа даёт эту цифру до старта.
    """
    plan = sample_size_for_proportion(0.10, 0.02, alpha=0.05, power=0.8)
    assert plan["sample_size_per_variant"] > 0
    assert plan["sample_size_total"] == plan["sample_size_per_variant"] * 2
