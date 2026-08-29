"""
Поправки на множественное тестирование.

Когда в одном эксперименте проверяется несколько метрик (или несколько
вариантов против контроля), вероятность хотя бы одного ложного открытия
растёт с числом сравнений: при 20 независимых тестах и alpha=0.05
ожидается примерно одно ложноположительное срабатывание.

Две поправки с разным смыслом:
- Бонферрони контролирует FWER — вероятность хотя бы одной ошибки.
  Консервативен, теряет реальные эффекты.
- Беньямини—Хохберг контролирует FDR — ожидаемую долю ошибок среди
  находок. Находит больше реального ценой некоторого числа ложных.
"""


def _validate(p_values):
    if not p_values:
        raise ValueError("Список p-values пуст")
    for p in p_values:
        if p is None or not (0.0 <= p <= 1.0):
            raise ValueError(f"Некорректный p-value: {p}")
    return list(p_values)


def bonferroni(p_values: list, alpha=0.05) -> dict:
    """
    Поправка Бонферрони: порог alpha/m для каждого теста.

    Эквивалентно домножению p-value на m (с обрезкой по 1.0).
    """
    p = _validate(p_values)
    m = len(p)
    adjusted = [min(1.0, pi * m) for pi in p]
    return {
        "method": "bonferroni",
        "controls": "FWER",
        "alpha": alpha,
        "n_tests": m,
        "threshold": alpha / m,
        "p_values": [round(x, 6) for x in p],
        "adjusted_p_values": [round(x, 6) for x in adjusted],
        "rejected": [bool(x < alpha) for x in adjusted],
        "n_rejected": sum(1 for x in adjusted if x < alpha),
    }


def benjamini_hochberg(p_values: list, alpha=0.05) -> dict:
    """
    Процедура Беньямини—Хохберга, контроль FDR.

    Отсортированные p(1)..p(m) сравниваются с i/m*alpha; отвергаются все
    гипотезы до наибольшего i, прошедшего порог. Скорректированные p-value
    (q-values) строятся монотонизацией справа налево — иначе q мог бы
    убывать с ростом p, что бессмысленно.
    """
    p = _validate(p_values)
    m = len(p)

    order = sorted(range(m), key=lambda i: p[i])
    q_sorted = [0.0] * m
    running_min = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        running_min = min(running_min, p[i] * m / (rank + 1))
        q_sorted[rank] = min(running_min, 1.0)

    adjusted = [0.0] * m
    for rank, i in enumerate(order):
        adjusted[i] = q_sorted[rank]

    return {
        "method": "benjamini_hochberg",
        "controls": "FDR",
        "alpha": alpha,
        "n_tests": m,
        "p_values": [round(x, 6) for x in p],
        "adjusted_p_values": [round(x, 6) for x in adjusted],
        "rejected": [bool(x < alpha) for x in adjusted],
        "n_rejected": sum(1 for x in adjusted if x < alpha),
    }


def correct(p_values: list, method="benjamini_hochberg", alpha=0.05) -> dict:
    """Точка входа для API: выбор поправки по имени."""
    if method == "bonferroni":
        return bonferroni(p_values, alpha)
    if method == "benjamini_hochberg":
        return benjamini_hochberg(p_values, alpha)
    if method == "none":
        p = _validate(p_values)
        return {
            "method": "none",
            "controls": None,
            "alpha": alpha,
            "n_tests": len(p),
            "p_values": [round(x, 6) for x in p],
            "adjusted_p_values": [round(x, 6) for x in p],
            "rejected": [bool(x < alpha) for x in p],
            "n_rejected": sum(1 for x in p if x < alpha),
            "warnings": [
                f"Поправка не применена при {len(p)} сравнениях: вероятность "
                f"хотя бы одного ложного открытия ≈ "
                f"{round((1 - (1 - alpha) ** len(p)) * 100, 1)}%, а не {alpha * 100}%."
            ],
        }
    raise ValueError(
        f"Неизвестный метод поправки: {method}. "
        f"Доступны: bonferroni, benjamini_hochberg, none"
    )
