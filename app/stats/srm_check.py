"""
Sample Ratio Mismatch — предохранитель эксперимента.

Расхождение фактического распределения по вариантам с заданным означает,
что механизм рандомизации или сбора данных сломан. В этом случае любой
посчитанный эффект недостоверен независимо от его p-value, поэтому SRM
проверяется до интерпретации результата.
"""
from scipy import stats

# Классическое правило применимости хи-квадрата: ожидаемая частота в каждой
# ячейке не меньше 5. Ниже этого порога p-value ненадёжен.
MIN_EXPECTED_PER_CELL = 5


def check_srm(observed_counts: list, expected_pcts: list, alpha=0.05) -> dict:
    """
    Хи-квадрат на соответствие фактического распределения заданному.

    Возвращает reliable=False, когда выборка слишком мала для самой проверки —
    это принципиально иное состояние, чем "перекоса нет", и не должно
    читаться как подтверждение корректности рандомизации.
    """
    if len(observed_counts) != len(expected_pcts):
        raise ValueError(
            f"Длины не совпадают: {len(observed_counts)} наблюдений "
            f"и {len(expected_pcts)} долей"
        )
    if len(observed_counts) < 2:
        raise ValueError("Для SRM нужно минимум 2 варианта")
    if any(c < 0 for c in observed_counts):
        raise ValueError("Число назначений не может быть отрицательным")

    total_pct = sum(expected_pcts)
    if abs(total_pct - 100.0) > 0.01:
        raise ValueError(f"Ожидаемые доли суммируются в {total_pct}, а не в 100")

    total = sum(observed_counts)
    if total == 0:
        raise ValueError("Нет ни одного назначения — SRM-проверка невозможна")

    expected = [total * p / 100 for p in expected_pcts]
    warnings = []

    reliable = min(expected) >= MIN_EXPECTED_PER_CELL
    if not reliable:
        warnings.append(
            f"Выборка слишком мала для SRM-проверки: минимальная ожидаемая частота "
            f"{min(expected):.1f} < {MIN_EXPECTED_PER_CELL}. Хи-квадрат ненадёжен, "
            f"результат проверки не следует трактовать как отсутствие перекоса."
        )

    chi2, p_value = stats.chisquare(observed_counts, expected)

    # На ненадёжной выборке сознательно не выносим вердикт о перекосе.
    srm_detected = bool(reliable and p_value < alpha)

    if srm_detected:
        warnings.append(
            f"Обнаружен SRM (p={p_value:.6f} < {alpha}): фактическое распределение "
            f"{[round(c / total * 100, 2) for c in observed_counts]}% отличается от "
            f"заданного {expected_pcts}%. Результаты эксперимента недостоверны — "
            f"проверьте механизм рандомизации и полноту сбора назначений."
        )

    return {
        "chi2": round(float(chi2), 6),
        "p_value": round(float(p_value), 6),
        "alpha": alpha,
        "srm_detected": srm_detected,
        "reliable": reliable,
        "total_assignments": total,
        "observed_counts": list(observed_counts),
        "observed_ratio": [round(c / total * 100, 2) for c in observed_counts],
        "expected_ratio": list(expected_pcts),
        "warnings": warnings,
    }
