"""
Блок 7. Difference-in-Differences.

DiD оценивает эффект без рандомизации, вычитая из изменения treatment-группы
изменение control-группы. Вся конструкция держится на допущении параллельных
трендов: без акции обе группы менялись бы одинаково. Поэтому проверка этого
допущения — не опциональное украшение, а часть метода.
"""
import numpy as np
import pytest

from stats.quasi_experimental import (
    difference_in_differences,
    check_parallel_trends,
    did_from_series,
)


# --- 7.1 известный синтетический эффект на фоне общего тренда ----------------

def make_panel(n_pre=8, n_post=8, trend=5.0, promo_effect=0.0, seed=42,
               control_trend=None, noise=3.0, base_t=100.0, base_c=90.0):
    """
    Дневные ряды treatment/control с общим рыночным трендом.
    promo_effect добавляется только treatment-группе и только после акции.
    """
    rng = np.random.default_rng(seed)
    ct = trend if control_trend is None else control_trend

    t_pre = [base_t + trend * i + rng.normal(0, noise) for i in range(n_pre)]
    c_pre = [base_c + ct * i + rng.normal(0, noise) for i in range(n_pre)]
    t_post = [base_t + trend * (n_pre + i) + promo_effect + rng.normal(0, noise)
              for i in range(n_post)]
    c_post = [base_c + ct * (n_pre + i) + rng.normal(0, noise)
              for i in range(n_post)]
    return t_pre, t_post, c_pre, c_post


def test_7_1_isolates_promo_effect_from_market_trend():
    """
    Обе группы растут на 5/день (рынок), treatment дополнительно +40 после акции.
    DiD обязан вернуть ~40, а не полный прирост treatment-группы.
    """
    t_pre, t_post, c_pre, c_post = make_panel(promo_effect=40.0, trend=5.0)
    res = difference_in_differences(t_pre, t_post, c_pre, c_post)

    assert abs(res["did_effect"] - 40.0) < 12, (
        f"DiD={res['did_effect']} вместо ~40. Наивная разница до/после в "
        f"treatment составила {res['delta_treatment']} — если DiD близок к ней, "
        f"тренд рынка не вычитается."
    )
    assert res["significant"], f"Эффект 40 должен быть значим: {res}"
    assert res["ci_lower"] < 40.0 < res["ci_upper"], "CI не накрывает истинный эффект"


def test_7_1b_no_effect_is_not_detected():
    """Акции не было → DiD не должен находить эффект, несмотря на общий рост."""
    t_pre, t_post, c_pre, c_post = make_panel(promo_effect=0.0, trend=8.0, seed=7)
    res = difference_in_differences(t_pre, t_post, c_pre, c_post)
    assert not res["significant"], (
        f"Ложноположительный DiD при отсутствии акции: {res['did_effect']}, "
        f"p={res['p_value']}. Общий тренд принят за эффект."
    )


def test_7_1c_does_not_confuse_seasonality_with_effect():
    """
    Сильная сезонность, влияющая на обе группы одинаково, не должна
    засчитываться как эффект акции.
    """
    rng = np.random.default_rng(3)
    season = [20 * np.sin(i / 3) for i in range(16)]
    t_pre = [100 + season[i] + rng.normal(0, 2) for i in range(8)]
    c_pre = [80 + season[i] + rng.normal(0, 2) for i in range(8)]
    t_post = [100 + season[8 + i] + rng.normal(0, 2) for i in range(8)]
    c_post = [80 + season[8 + i] + rng.normal(0, 2) for i in range(8)]

    res = difference_in_differences(t_pre, t_post, c_pre, c_post)
    assert not res["significant"], f"Сезонность принята за эффект акции: {res}"


@pytest.mark.slow
def test_7_1d_did_false_positive_rate():
    """AA-режим для DiD: при отсутствии эффекта FPR должен быть ≈alpha."""
    fp = 0
    sims = 300
    for s in range(sims):
        t_pre, t_post, c_pre, c_post = make_panel(
            promo_effect=0.0, trend=4.0, seed=1000 + s, n_pre=20, n_post=20
        )
        if difference_in_differences(
            t_pre, t_post, c_pre, c_post, n_iterations=1000
        )["significant"]:
            fp += 1
    fpr = fp / sims
    assert fpr < 0.12, f"DiD FPR={fpr:.3f} — слишком много ложных срабатываний"


# --- 7.2 нарушение параллельных трендов -------------------------------------

def test_7_2_flags_non_parallel_pre_trends():
    """
    Control рос на 1/день, treatment на 9/день ещё ДО акции.
    Допущение DiD нарушено — платформа обязана предупредить.
    """
    t_pre, t_post, c_pre, c_post = make_panel(
        promo_effect=0.0, trend=9.0, control_trend=1.0, noise=1.0, seed=5
    )
    res = difference_in_differences(t_pre, t_post, c_pre, c_post)

    assert res["parallel_trends"]["violated"] is True, (
        f"Нарушение параллельных трендов не обнаружено: {res['parallel_trends']}"
    )
    assert res["warnings"], "Нет предупреждения при нарушенном допущении"


def test_7_2b_parallel_trends_pass_when_parallel():
    """При действительно параллельных трендах предупреждения быть не должно."""
    t_pre, t_post, c_pre, c_post = make_panel(
        promo_effect=30.0, trend=5.0, control_trend=5.0, noise=2.0, seed=9
    )
    res = difference_in_differences(t_pre, t_post, c_pre, c_post)
    assert res["parallel_trends"]["violated"] is False, (
        f"Ложное срабатывание проверки трендов: {res['parallel_trends']}"
    )


def test_7_2c_check_parallel_trends_standalone():
    """Функция проверки трендов должна сравнивать наклоны, а не уровни."""
    # Разные уровни, одинаковые наклоны — тренды параллельны.
    same_slope = check_parallel_trends(
        [100, 105, 110, 115, 120], [50, 55, 60, 65, 70]
    )
    assert same_slope["violated"] is False, f"Разные уровни приняты за разные тренды: {same_slope}"

    # Одинаковый старт, разные наклоны — тренды не параллельны.
    diff_slope = check_parallel_trends(
        [100, 110, 120, 130, 140], [100, 102, 104, 106, 108]
    )
    assert diff_slope["violated"] is True, f"Разные наклоны не обнаружены: {diff_slope}"


def test_7_2d_parallel_trends_needs_enough_periods():
    """Меньше 3 точек до акции — проверить тренд невозможно, нужен честный отказ."""
    res = check_parallel_trends([100, 110], [50, 55])
    assert res["testable"] is False
    assert res["warnings"]


# --- 7.3 отсутствие pre-периода ---------------------------------------------

def test_7_3_empty_pre_period_raises():
    """Нет данных до акции — DiD физически невозможен."""
    with pytest.raises(ValueError):
        difference_in_differences([], [100, 110], [90, 95], [95, 100])


def test_7_3b_none_values_raise():
    with pytest.raises(ValueError):
        difference_in_differences([100, None], [110, 120], [90, 95], [95, 100])


def test_7_3c_series_helper_excludes_skus_without_history():
    """
    did_from_series: SKU без продаж до акции (новый товар) должен
    исключаться явно, с указанием в отчёте, а не портить расчёт.
    """
    treatment = {
        "SKU-A": {"pre": [100, 105, 110], "post": [150, 155, 160]},
        "SKU-NEW": {"pre": [], "post": [200, 210, 220]},  # появился с акцией
    }
    control = {
        "SKU-B": {"pre": [90, 95, 100], "post": [100, 105, 110]},
    }
    res = did_from_series(treatment, control)

    assert "SKU-NEW" in res["excluded_entities"], (
        f"SKU без pre-периода не исключён: {res['excluded_entities']}"
    )
    assert "SKU-A" not in res["excluded_entities"]
    assert res["warnings"], "Исключение сущностей должно сопровождаться предупреждением"


def test_7_3d_all_treatment_excluded_raises():
    """Если исключить нечего оставить — явная ошибка."""
    treatment = {"SKU-NEW": {"pre": [], "post": [200, 210]}}
    control = {"SKU-B": {"pre": [90, 95], "post": [100, 105]}}
    with pytest.raises(ValueError):
        did_from_series(treatment, control)


# --- корректность вывода -----------------------------------------------------

def test_7_4_did_identity_holds():
    """did_effect должен в точности равняться delta_treatment - delta_control."""
    t_pre, t_post, c_pre, c_post = make_panel(promo_effect=25.0, seed=11)
    res = difference_in_differences(t_pre, t_post, c_pre, c_post)
    assert res["did_effect"] == pytest.approx(
        res["delta_treatment"] - res["delta_control"], abs=1e-3
    )


def test_7_5_json_safe_and_pvalue_bounded():
    """Ни nan/inf, ни нулевого p-value в ответе."""
    t_pre, t_post, c_pre, c_post = make_panel(promo_effect=500.0, noise=0.5, seed=2)
    res = difference_in_differences(t_pre, t_post, c_pre, c_post, n_iterations=1000)
    assert 0.0 < res["p_value"] <= 1.0, f"Некорректный p-value: {res['p_value']}"
    for k, v in res.items():
        if isinstance(v, float):
            assert np.isfinite(v), f"Поле {k} = {v}"


def test_7_6_reproducible():
    t_pre, t_post, c_pre, c_post = make_panel(promo_effect=20.0, seed=4)
    a = difference_in_differences(t_pre, t_post, c_pre, c_post, seed=7)
    b = difference_in_differences(t_pre, t_post, c_pre, c_post, seed=7)
    assert a["did_effect"] == b["did_effect"] and a["ci_lower"] == b["ci_lower"]
