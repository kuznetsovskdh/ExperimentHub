"""
Классические частотные тесты для AB-экспериментов.

Два инварианта, которые здесь соблюдаются намеренно:

1. Возвращаемые числа всегда JSON-сериализуемы — никаких nan/inf.
   Вырожденные данные (нулевая дисперсия, нулевые/полные конверсии) — это
   штатная ситуация продакшена, а не повод отдать 500.
2. p-value и доверительный интервал строятся по ОДНОЙ И ТОЙ ЖЕ модели.
   Рассогласование (например, Стьюдент для p-value и Уэлч для CI) даёт
   систематически заниженный p-value при неравных дисперсиях.
"""
import numpy as np
from scipy import stats


def _validate_proportions(n_control, conv_control, n_treatment, conv_treatment):
    if n_control <= 0 or n_treatment <= 0:
        raise ValueError(
            f"Размер группы должен быть > 0 (control={n_control}, treatment={n_treatment})"
        )
    if conv_control < 0 or conv_treatment < 0:
        raise ValueError("Число конверсий не может быть отрицательным")
    if conv_control > n_control or conv_treatment > n_treatment:
        raise ValueError(
            f"Конверсий больше размера выборки: "
            f"control {conv_control}/{n_control}, treatment {conv_treatment}/{n_treatment}"
        )


def z_test_proportions(n_control, conv_control, n_treatment, conv_treatment, alpha=0.05):
    """
    Z-тест для разности пропорций (двусторонний, pooled SE).

    Совпадает с statsmodels.stats.proportion.proportions_ztest([c_t, c_c], [n_t, n_c]).
    CI строится по несопряжённой (unpooled) оценке SE — стандартная практика:
    тест проверяет H0 о равенстве, интервал оценивает фактическую разность.
    """
    _validate_proportions(n_control, conv_control, n_treatment, conv_treatment)

    p1 = conv_control / n_control
    p2 = conv_treatment / n_treatment
    effect_size = p2 - p1
    warnings = []

    p_pool = (conv_control + conv_treatment) / (n_control + n_treatment)
    se_pooled = np.sqrt(p_pool * (1 - p_pool) * (1 / n_control + 1 / n_treatment))

    if se_pooled == 0:
        # Все наблюдения конвертировались либо ни одно — вариации нет вовсе,
        # z-статистика не определена. Различия между группами тоже нет.
        warnings.append(
            "Нулевая дисперсия: конверсия одинакова и вырождена в обеих группах "
            f"(p={p1:.4f}). Статистический вывод невозможен."
        )
        z = 0.0
        p_value = 1.0
    else:
        z = (p2 - p1) / se_pooled
        p_value = 2 * stats.norm.sf(abs(z))

    z_crit = stats.norm.ppf(1 - alpha / 2)
    se_unpooled = np.sqrt(p1 * (1 - p1) / n_control + p2 * (1 - p2) / n_treatment)
    ci_lower = effect_size - z_crit * se_unpooled
    ci_upper = effect_size + z_crit * se_unpooled

    if min(conv_control, conv_treatment, n_control - conv_control,
           n_treatment - conv_treatment) < 5:
        warnings.append(
            "В одной из ячеек меньше 5 наблюдений — нормальная аппроксимация "
            "z-теста ненадёжна, предпочтителен точный тест Фишера или bootstrap."
        )

    return {
        "method": "z_test",
        "statistic": round(float(z), 6),
        "p_value": round(float(p_value), 6),
        "effect_size": round(float(effect_size), 6),
        "ci_lower": round(float(ci_lower), 6),
        "ci_upper": round(float(ci_upper), 6),
        "alpha": alpha,
        "significant": bool(p_value < alpha),
        "warnings": warnings,
    }


def t_test_continuous(control_values, treatment_values, alpha=0.05):
    """
    Тест Уэлча для разности средних (двусторонний, не предполагает равных дисперсий).

    Уэлч, а не Стьюдент — сознательный выбор: в AB-тестах группы регулярно
    имеют и разный размер, и разную дисперсию (treatment меняет поведение,
    а не только среднее). Стьюдент в этих условиях занижает p-value.
    CI строится по t-распределению с тем же df Уэлча—Саттертуэйта, что и тест.
    """
    ctrl = np.asarray(control_values, dtype=float)
    trt = np.asarray(treatment_values, dtype=float)

    if ctrl.size < 2 or trt.size < 2:
        raise ValueError(
            f"Для t-теста нужно минимум 2 наблюдения в каждой группе "
            f"(получено control={ctrl.size}, treatment={trt.size})"
        )
    if not np.all(np.isfinite(ctrl)) or not np.all(np.isfinite(trt)):
        raise ValueError("Входные данные содержат nan/inf")

    n1, n2 = ctrl.size, trt.size
    var1, var2 = np.var(ctrl, ddof=1), np.var(trt, ddof=1)
    effect_size = float(np.mean(trt) - np.mean(ctrl))
    warnings = []

    se = np.sqrt(var1 / n1 + var2 / n2)

    if se == 0:
        # Обе группы — константы. Классический вырожденный случай.
        warnings.append(
            "Нулевая дисперсия в обеих группах: t-статистика не определена."
        )
        t_stat = 0.0
        p_value = 1.0 if effect_size == 0 else 0.0
        df = float(n1 + n2 - 2)
        ci_lower = ci_upper = effect_size
    else:
        t_stat, p_value = stats.ttest_ind(ctrl, trt, equal_var=False)
        t_stat = -float(t_stat)  # scipy считает control-treatment, нам нужен обратный знак
        # Уэлч—Саттертуэйт
        df = (var1 / n1 + var2 / n2) ** 2 / (
            (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
        )
        t_crit = stats.t.ppf(1 - alpha / 2, df)
        ci_lower = effect_size - t_crit * se
        ci_upper = effect_size + t_crit * se

    if min(n1, n2) < 30:
        warnings.append(
            f"Малая выборка (min n={min(n1, n2)}): результат чувствителен к выбросам, "
            f"стоит перепроверить bootstrap-методом."
        )

    return {
        "method": "t_test",
        "statistic": round(float(t_stat), 6),
        "df": round(float(df), 4),
        "p_value": round(float(p_value), 6),
        "effect_size": round(float(effect_size), 6),
        "ci_lower": round(float(ci_lower), 6),
        "ci_upper": round(float(ci_upper), 6),
        "alpha": alpha,
        "significant": bool(p_value < alpha),
        "warnings": warnings,
    }
