"""
Блок 4. CUPED.

CUPED снижает дисперсию метрики, вычитая объяснённую предэкспериментальным
значением часть: Y_cuped = Y - theta*(X - mean(X)), theta = cov(Y,X)/var(X).

Главный риск реализации — посчитать theta и центрирование ОТДЕЛЬНО по группам.
Тогда преобразование становится функцией от групповых средних и вносит
смещение в оценку эффекта. theta и mean(X) должны быть общими для всего
эксперимента.
"""
import numpy as np
import pytest

from stats.cuped import apply_cuped, cuped_variance_reduction, cuped_adjust_groups
from stats.frequentist import t_test_continuous


def correlated_data(n, rho, seed=42):
    """Пара (pre, post) с заданной корреляцией."""
    rng = np.random.default_rng(seed)
    pre = rng.normal(10, 3, n)
    noise = rng.normal(0, 3 * np.sqrt(1 - rho ** 2), n)
    post = rho * (pre - 10) + 10 + noise
    return pre, post


# --- 4.1 снижение дисперсии при сильной корреляции --------------------------

def test_4_1_reduces_variance_with_strong_correlation():
    """rho≈0.8 → дисперсия должна упасть заметно (теоретически на ~rho^2 = 64%)."""
    pre, post = correlated_data(5000, 0.8)
    res = cuped_variance_reduction(post.tolist(), pre.tolist())
    assert res["reduction_pct"] > 50, (
        f"При rho=0.8 ожидалось снижение дисперсии >50%, получено "
        f"{res['reduction_pct']}%: {res}"
    )


def test_4_1b_reduction_matches_rho_squared():
    """Снижение дисперсии должно быть близко к rho^2 — прямая проверка формулы."""
    for rho in (0.3, 0.5, 0.7, 0.9):
        pre, post = correlated_data(20_000, rho, seed=int(rho * 100))
        res = cuped_variance_reduction(post.tolist(), pre.tolist())
        expected = rho ** 2 * 100
        assert abs(res["reduction_pct"] - expected) < 5, (
            f"rho={rho}: снижение {res['reduction_pct']}%, ожидалось ~{expected:.1f}%"
        )


def test_4_1c_mean_is_preserved():
    """CUPED не должен сдвигать среднее — он снижает только дисперсию."""
    pre, post = correlated_data(5000, 0.8)
    adjusted = apply_cuped(post.tolist(), pre.tolist())
    assert np.mean(adjusted) == pytest.approx(np.mean(post), abs=1e-9)


# --- 4.2 нулевая корреляция → CUPED не вредит -------------------------------

def test_4_2_no_harm_with_zero_correlation():
    """При независимых pre/post дисперсия не должна вырасти."""
    rng = np.random.default_rng(7)
    pre = rng.normal(10, 3, 5000)
    post = rng.normal(10, 3, 5000)
    res = cuped_variance_reduction(post.tolist(), pre.tolist())
    assert res["reduction_pct"] > -1.0, (
        f"CUPED увеличил дисперсию на некоррелированных данных: {res}"
    )
    assert res["reduction_pct"] < 5, f"Подозрительно большое снижение при rho=0: {res}"


def test_4_2b_zero_variance_pre_period():
    """Все pre-значения одинаковы → theta не определена, нужен явный отказ."""
    with pytest.raises(ValueError):
        apply_cuped([1.0, 2.0, 3.0] * 10, [5.0] * 30)


# --- 4.3 CUPED повышает чувствительность ------------------------------------

def test_4_3_cuped_increases_sensitivity():
    """
    Один и тот же реальный эффект под CUPED должен детектироваться увереннее
    (меньший p-value) при том же размере выборки.
    """
    rng = np.random.default_rng(123)
    n, rho, true_effect = 800, 0.8, 0.5

    pre_c = rng.normal(10, 3, n)
    pre_t = rng.normal(10, 3, n)
    noise_scale = 3 * np.sqrt(1 - rho ** 2)
    post_c = rho * (pre_c - 10) + 10 + rng.normal(0, noise_scale, n)
    post_t = rho * (pre_t - 10) + 10 + true_effect + rng.normal(0, noise_scale, n)

    plain = t_test_continuous(post_c.tolist(), post_t.tolist())
    adj_c, adj_t = cuped_adjust_groups(
        post_c.tolist(), pre_c.tolist(), post_t.tolist(), pre_t.tolist()
    )
    cuped = t_test_continuous(adj_c, adj_t)

    assert cuped["p_value"] < plain["p_value"], (
        f"CUPED не повысил чувствительность: p_plain={plain['p_value']}, "
        f"p_cuped={cuped['p_value']}"
    )
    assert (cuped["ci_upper"] - cuped["ci_lower"]) < (plain["ci_upper"] - plain["ci_lower"]), \
        "CUPED должен сузить доверительный интервал"


def test_4_3b_cuped_does_not_bias_effect_estimate():
    """
    Ключевой тест корректности: CUPED снижает дисперсию, но НЕ смещает оценку
    эффекта. Прогоняем много симуляций и сверяем средний эффект с истинным.
    """
    rng = np.random.default_rng(555)
    n, rho, true_effect = 400, 0.8, 0.5
    noise_scale = 3 * np.sqrt(1 - rho ** 2)

    estimates = []
    for _ in range(300):
        pre_c = rng.normal(10, 3, n)
        pre_t = rng.normal(10, 3, n)
        post_c = rho * (pre_c - 10) + 10 + rng.normal(0, noise_scale, n)
        post_t = rho * (pre_t - 10) + 10 + true_effect + rng.normal(0, noise_scale, n)
        adj_c, adj_t = cuped_adjust_groups(
            post_c.tolist(), pre_c.tolist(), post_t.tolist(), pre_t.tolist()
        )
        estimates.append(np.mean(adj_t) - np.mean(adj_c))

    mean_estimate = float(np.mean(estimates))
    assert abs(mean_estimate - true_effect) < 0.03, (
        f"CUPED смещает оценку эффекта: среднее по 300 симуляциям "
        f"{mean_estimate:.4f} против истинного {true_effect}. "
        f"Вероятно theta/центрирование считаются отдельно по группам."
    )


@pytest.mark.slow
def test_4_3c_cuped_preserves_false_positive_rate():
    """
    AA-тест под CUPED: при отсутствии эффекта доля ложных срабатываний
    должна остаться ≈alpha. Некорректный CUPED раздувает её.
    """
    rng = np.random.default_rng(777)
    n, rho = 300, 0.8
    noise_scale = 3 * np.sqrt(1 - rho ** 2)
    fp = 0
    sims = 600
    for _ in range(sims):
        pre_c = rng.normal(10, 3, n)
        pre_t = rng.normal(10, 3, n)
        post_c = rho * (pre_c - 10) + 10 + rng.normal(0, noise_scale, n)
        post_t = rho * (pre_t - 10) + 10 + rng.normal(0, noise_scale, n)
        adj_c, adj_t = cuped_adjust_groups(
            post_c.tolist(), pre_c.tolist(), post_t.tolist(), pre_t.tolist()
        )
        if t_test_continuous(adj_c, adj_t)["significant"]:
            fp += 1
    fpr = fp / sims
    assert abs(fpr - 0.05) < 0.025, (
        f"CUPED ломает уровень ошибки первого рода: FPR={fpr:.4f}, ожидалось ~0.05"
    )


# --- 4.4 неполные pre-данные ------------------------------------------------

def test_4_4_length_mismatch_raises():
    """Разная длина values и pre_values — явная ошибка, не тихий обрез."""
    with pytest.raises(ValueError):
        apply_cuped([1.0, 2.0, 3.0], [1.0, 2.0])


def test_4_4b_none_in_pre_values_raises():
    """None среди pre-значений (новый пользователь без истории) — явная ошибка."""
    with pytest.raises(ValueError):
        apply_cuped([1.0, 2.0, 3.0], [1.0, None, 3.0])


def test_4_4c_shared_theta_between_groups():
    """
    cuped_adjust_groups должен использовать ОДНУ theta и ОДНО общее mean(X)
    для обеих групп. Проверяем: если склеить группы и применить apply_cuped
    целиком, результат обязан совпасть.
    """
    rng = np.random.default_rng(31)
    pre_c, post_c = rng.normal(10, 3, 200), rng.normal(12, 3, 200)
    pre_t, post_t = rng.normal(10, 3, 200), rng.normal(13, 3, 200)

    adj_c, adj_t = cuped_adjust_groups(
        post_c.tolist(), pre_c.tolist(), post_t.tolist(), pre_t.tolist()
    )
    pooled = apply_cuped(
        np.concatenate([post_c, post_t]).tolist(),
        np.concatenate([pre_c, pre_t]).tolist(),
    )
    np.testing.assert_allclose(adj_c + adj_t, pooled, atol=1e-9)
