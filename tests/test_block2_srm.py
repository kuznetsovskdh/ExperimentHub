"""
Блок 2. SRM (Sample Ratio Mismatch).

SRM — предохранитель платформы: он должен срабатывать ДО того, как аналитик
посмотрит на эффект. Ложное срабатывание обесценивает предохранитель,
пропуск реального перекоса — обесценивает весь эксперимент.
"""
import numpy as np
import pytest

from stats.srm_check import check_srm


# --- 2.1 честное распределение → нет ложных срабатываний ---------------------

def test_2_1_honest_5050_no_false_alarm():
    """Ровно 50/50 на большой выборке — SRM молчит."""
    res = check_srm([50_000, 50_000], [50.0, 50.0])
    assert not res["srm_detected"], f"Ложное срабатывание SRM на честных данных: {res}"


@pytest.mark.slow
def test_2_1b_srm_false_positive_rate():
    """
    Честная рандомизация, 1000 прогонов → SRM должен срабатывать примерно в alpha
    случаев, не чаще. Иначе аналитики начнут игнорировать предупреждение.
    """
    rng = np.random.default_rng(42)
    n = 20_000
    false_alarms = 0
    for _ in range(1000):
        a = int(rng.binomial(n, 0.5))
        res = check_srm([a, n - a], [50.0, 50.0])
        if res["srm_detected"]:
            false_alarms += 1
    fpr = false_alarms / 1000
    assert abs(fpr - 0.05) < 0.02, f"SRM FPR={fpr:.4f}, ожидалось ~0.05"


def test_2_1c_honest_unequal_split():
    """Честный 90/10 не должен помечаться как SRM."""
    res = check_srm([90_000, 10_000], [90.0, 10.0])
    assert not res["srm_detected"], f"Ложное срабатывание на честном 90/10: {res}"


# --- 2.2 реальный перекос → срабатывание ------------------------------------

def test_2_2_detects_realistic_skew():
    """
    Баг в клиенте: 55% вместо 50% при n=100000. Классический SRM,
    платформа обязана его увидеть.
    """
    res = check_srm([55_000, 45_000], [50.0, 50.0])
    assert res["srm_detected"], f"SRM не обнаружен при перекосе 55/45: {res}"
    assert res["p_value"] < 0.001


def test_2_2b_detects_subtle_skew_on_large_sample():
    """51/49 при n=1000000 — тонкий, но реальный перекос."""
    res = check_srm([510_000, 490_000], [50.0, 50.0])
    assert res["srm_detected"], f"SRM не обнаружен при 51/49 на 1M: {res}"


def test_2_2c_srm_result_is_actionable():
    """Ответ SRM должен нести человекочитаемое объяснение, а не только chi2/p."""
    res = check_srm([55_000, 45_000], [50.0, 50.0])
    assert "observed_ratio" in res and "expected_ratio" in res, (
        f"В ответе SRM нет фактического и ожидаемого распределения: {res}"
    )
    assert res["warnings"], "При обнаруженном SRM должно быть явное предупреждение"


# --- 2.3 малые выборки → предупреждение, а не ложный вывод -------------------

def test_2_3_small_sample_is_flagged_as_unreliable():
    """
    Хи-квадрат ненадёжен при малых ожидаемых частотах (правило: ожидаемая >= 5).
    Платформа должна явно сказать, что проверки не было, а не молча вернуть p.
    """
    res = check_srm([3, 5], [50.0, 50.0])
    assert res["reliable"] is False, (
        f"SRM на выборке из 8 наблюдений помечен как надёжный: {res}"
    )
    assert res["warnings"], "Нет предупреждения о недостаточном размере выборки"


def test_2_3b_small_sample_does_not_false_alarm():
    """На крошечной выборке SRM не должен объявлять перекос."""
    res = check_srm([2, 6], [50.0, 50.0])
    assert not res["srm_detected"], (
        f"Ложное срабатывание SRM на n=8: {res}. "
        f"Малая выборка — причина воздержаться от вывода, а не сделать его."
    )


def test_2_3c_sufficient_sample_is_reliable():
    """При ожидаемых частотах >= 5 проверка помечается надёжной."""
    res = check_srm([500, 520], [50.0, 50.0])
    assert res["reliable"] is True


# --- валидация входа ---------------------------------------------------------

def test_2_4_zero_total_raises():
    """Ни одного назначения — нечего проверять, явная ошибка."""
    with pytest.raises(ValueError):
        check_srm([0, 0], [50.0, 50.0])


def test_2_4b_length_mismatch_raises():
    with pytest.raises(ValueError):
        check_srm([100, 100], [50.0, 25.0, 25.0])


def test_2_4c_allocations_not_summing_to_100_raises():
    with pytest.raises(ValueError):
        check_srm([100, 100], [50.0, 30.0])


def test_2_5_three_variants():
    """SRM работает не только для двух вариантов."""
    ok = check_srm([33_300, 33_300, 33_400], [33.3, 33.3, 33.4])
    assert not ok["srm_detected"]
    bad = check_srm([40_000, 30_000, 30_000], [33.3, 33.3, 33.4])
    assert bad["srm_detected"]
