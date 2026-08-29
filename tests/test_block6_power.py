"""
Блок 6. Power analysis.

Главный тест блока (6.1) — замкнутый цикл: посчитать размер выборки,
сгенерировать ровно такой эксперимент с ровно таким эффектом и убедиться,
что эффект находится примерно в `power` доле прогонов. Это проверяет
формулу целиком, а не её отдельные множители.
"""
import numpy as np
import pytest

from stats.power_analysis import sample_size_for_proportion, achieved_power
from stats.frequentist import z_test_proportions


# --- 6.1 обратная проверка симуляцией ---------------------------------------

@pytest.mark.slow
@pytest.mark.parametrize(
    "baseline,mde,power",
    [(0.10, 0.02, 0.80), (0.20, 0.05, 0.80), (0.05, 0.02, 0.90)],
)
def test_6_1_sample_size_delivers_promised_power(baseline, mde, power):
    """Выборка рассчитанного размера должна давать заявленную мощность."""
    calc = sample_size_for_proportion(baseline, mde, alpha=0.05, power=power)
    n = calc["sample_size_per_variant"]

    rng = np.random.default_rng(2024)
    sims = 1000
    detected = 0
    for _ in range(sims):
        c = int(rng.binomial(n, baseline))
        t = int(rng.binomial(n, baseline + mde))
        if z_test_proportions(n, c, n, t, alpha=0.05)["significant"]:
            detected += 1

    empirical = detected / sims
    assert abs(empirical - power) < 0.04, (
        f"baseline={baseline}, mde={mde}: расчёт дал n={n} на вариант, "
        f"фактическая мощность {empirical:.3f} против заявленной {power}. "
        f"Формула размера выборки некорректна."
    )


def test_6_1b_sample_size_scales_correctly():
    """Меньший MDE требует большей выборки, примерно как 1/MDE^2."""
    n1 = sample_size_for_proportion(0.10, 0.04)["sample_size_per_variant"]
    n2 = sample_size_for_proportion(0.10, 0.02)["sample_size_per_variant"]
    ratio = n2 / n1
    assert 3.2 < ratio < 4.8, (
        f"Уменьшение MDE вдвое изменило выборку в {ratio:.2f} раза, ожидалось ~4"
    )


def test_6_1c_higher_power_requires_more_sample():
    n80 = sample_size_for_proportion(0.10, 0.02, power=0.80)["sample_size_per_variant"]
    n90 = sample_size_for_proportion(0.10, 0.02, power=0.90)["sample_size_per_variant"]
    assert n90 > n80


def test_6_1d_stricter_alpha_requires_more_sample():
    n05 = sample_size_for_proportion(0.10, 0.02, alpha=0.05)["sample_size_per_variant"]
    n01 = sample_size_for_proportion(0.10, 0.02, alpha=0.01)["sample_size_per_variant"]
    assert n01 > n05


# --- 6.2 достигнутая мощность постфактум ------------------------------------

def test_6_2_achieved_power_is_low_for_small_sample():
    """Маленькая выборка при маленьком эффекте → низкая мощность."""
    res = achieved_power(n=100, baseline_rate=0.10, observed_effect=0.01)
    assert res["achieved_power"] < 0.2, f"Ожидалась низкая мощность: {res}"


def test_6_2b_achieved_power_is_high_for_large_sample():
    res = achieved_power(n=50_000, baseline_rate=0.10, observed_effect=0.02)
    assert res["achieved_power"] > 0.95, f"Ожидалась высокая мощность: {res}"


def test_6_2c_achieved_power_roundtrips_with_sample_size():
    """
    Согласованность двух функций: на выборке, рассчитанной под power=0.8,
    достигнутая мощность при том же эффекте должна быть ≈0.8.
    """
    calc = sample_size_for_proportion(0.10, 0.02, alpha=0.05, power=0.80)
    res = achieved_power(calc["sample_size_per_variant"], 0.10, 0.02, alpha=0.05)
    assert abs(res["achieved_power"] - 0.80) < 0.05, (
        f"Функции рассинхронизированы: n={calc['sample_size_per_variant']} "
        f"рассчитан под 0.8, но achieved_power={res['achieved_power']}"
    )


def test_6_2d_achieved_power_symmetric_in_effect_sign():
    """Мощность зависит от величины эффекта, а не от его знака."""
    up = achieved_power(5000, 0.20, 0.03)["achieved_power"]
    down = achieved_power(5000, 0.20, -0.03)["achieved_power"]
    assert abs(up - down) < 0.02, f"Мощность несимметрична по знаку: {up} vs {down}"


# --- 6.3 граничные параметры ------------------------------------------------

def test_6_3_zero_mde_raises():
    """MDE=0 требует бесконечной выборки — явная ошибка вместо inf."""
    with pytest.raises(ValueError):
        sample_size_for_proportion(0.10, 0.0)


def test_6_3b_invalid_baseline_raises():
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            sample_size_for_proportion(bad, 0.02)


def test_6_3c_mde_pushing_rate_out_of_range_raises():
    """baseline 0.95 + MDE 0.10 = 1.05 — конверсия выше 100% невозможна."""
    with pytest.raises(ValueError):
        sample_size_for_proportion(0.95, 0.10)


def test_6_3d_invalid_alpha_power_raise():
    with pytest.raises(ValueError):
        sample_size_for_proportion(0.10, 0.02, alpha=0.0)
    with pytest.raises(ValueError):
        sample_size_for_proportion(0.10, 0.02, alpha=1.0)
    with pytest.raises(ValueError):
        sample_size_for_proportion(0.10, 0.02, power=1.0)
    with pytest.raises(ValueError):
        sample_size_for_proportion(0.10, 0.02, power=0.0)


def test_6_3e_extreme_but_valid_params_do_not_explode():
    """power=0.999 и крошечный MDE — огромная, но конечная и валидная выборка."""
    res = sample_size_for_proportion(0.10, 0.001, alpha=0.001, power=0.999)
    n = res["sample_size_per_variant"]
    assert np.isfinite(n) and n > 0
    assert isinstance(n, int)


def test_6_3f_achieved_power_validates_input():
    with pytest.raises(ValueError):
        achieved_power(0, 0.10, 0.02)
    with pytest.raises(ValueError):
        achieved_power(100, 1.5, 0.02)


def test_6_3g_achieved_power_effect_out_of_range():
    """baseline 0.98 + эффект 0.05 выводит конверсию за 100%."""
    with pytest.raises(ValueError):
        achieved_power(1000, 0.98, 0.05)
