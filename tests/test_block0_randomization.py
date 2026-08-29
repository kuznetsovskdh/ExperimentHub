"""
Блок 0. Рандомизация и Assignment (чистая hash-функция, без HTTP).

Проверяется математика бакетирования: детерминированность, равномерность,
корректность неравного сплита, независимость экспериментов, устойчивость
к пограничным entity_id.
"""
import pytest
from scipy import stats

from stats.randomization import assign_variant


class V:
    """Минимальный стенд-ин для ORM-модели Variant."""

    def __init__(self, id, allocation_pct, name=""):
        self.id = id
        self.allocation_pct = allocation_pct
        self.name = name


def split_5050():
    return [V(1, 50.0, "control"), V(2, 50.0, "treatment")]


def split_9010():
    return [V(1, 90.0, "control"), V(2, 10.0, "treatment")]


# --- 0.1 детерминированность -------------------------------------------------

def test_0_1_assignment_is_deterministic():
    """Один entity_id в одном эксперименте → всегда один и тот же вариант."""
    variants = split_5050()
    results = {assign_variant("user-42", 1, variants) for _ in range(100)}
    assert len(results) == 1, f"Назначение недетерминировано: получено {results}"


def test_0_1b_deterministic_across_many_entities():
    """Детерминированность держится для выборки разных entity_id."""
    variants = split_5050()
    for i in range(500):
        eid = f"user-{i}"
        first = assign_variant(eid, 1, variants)
        assert all(assign_variant(eid, 1, variants) == first for _ in range(3))


# --- 0.2 равномерность 50/50 -------------------------------------------------

@pytest.mark.slow
def test_0_2_uniform_split_chi2():
    """100k entity_id при 50/50 → распределение статистически неотличимо от 50/50."""
    variants = split_5050()
    n = 100_000
    counts = {1: 0, 2: 0}
    for i in range(n):
        counts[assign_variant(f"entity-{i}", 1, variants)] += 1

    chi2, p = stats.chisquare([counts[1], counts[2]], [n / 2, n / 2])
    share = counts[1] / n
    assert p > 0.01, (
        f"Распределение отличается от 50/50: {counts}, доля control={share:.4f}, "
        f"chi2={chi2:.2f}, p={p:.5f}"
    )


# --- 0.3 неравный сплит ------------------------------------------------------

@pytest.mark.slow
def test_0_3_unequal_split_90_10():
    """90/10 split должен давать ~90/10, а не ~50/50."""
    variants = split_9010()
    n = 100_000
    counts = {1: 0, 2: 0}
    for i in range(n):
        counts[assign_variant(f"entity-{i}", 1, variants)] += 1

    share_control = counts[1] / n
    assert abs(share_control - 0.90) < 0.01, (
        f"90/10 split реализован неверно: доля control={share_control:.4f}, {counts}"
    )


def test_0_3b_three_way_split():
    """Сплит на 3 варианта 34/33/33 — все варианты должны получать трафик."""
    variants = [V(1, 34.0), V(2, 33.0), V(3, 33.0)]
    counts = {1: 0, 2: 0, 3: 0}
    for i in range(30_000):
        counts[assign_variant(f"e{i}", 7, variants)] += 1
    for vid, c in counts.items():
        assert c > 0, f"Вариант {vid} не получил ни одной сущности: {counts}"
    shares = {k: v / 30_000 for k, v in counts.items()}
    assert all(abs(s - 1 / 3) < 0.02 for s in shares.values()), f"Перекос: {shares}"


# --- 0.4 независимость экспериментов ----------------------------------------

@pytest.mark.slow
def test_0_4_experiments_are_independent():
    """
    Назначение в эксперименте A не должно предсказывать назначение в эксперименте B.
    Проверяется хи-квадратом на таблице сопряжённости 2x2.
    """
    variants_a = split_5050()
    variants_b = [V(10, 50.0), V(11, 50.0)]

    table = [[0, 0], [0, 0]]
    for i in range(50_000):
        eid = f"entity-{i}"
        a = assign_variant(eid, 1, variants_a)
        b = assign_variant(eid, 2, variants_b)
        table[0 if a == 1 else 1][0 if b == 10 else 1] += 1

    chi2, p, _, _ = stats.chi2_contingency(table)
    assert p > 0.01, (
        f"Назначения в разных экспериментах коррелируют (chi2={chi2:.1f}, p={p:.6f}). "
        f"Таблица: {table}. Вероятно experiment_id учтён в хэше некорректно."
    )


def test_0_4b_no_key_collision_between_entity_and_experiment():
    """
    Ключ хэша должен однозначно разделять entity_id и experiment_id.
    Конкатенация без разделителя даёт коллизию: ("1", 12) и ("11", 2) → "112".
    """
    variants = split_5050()
    pairs = [(("1", 12), ("11", 2)), (("12", 3), ("1", 23)), (("7", 89), ("78", 9))]

    collisions = []
    for (e1, x1), (e2, x2) in pairs:
        # Разные пары (entity, experiment) не обязаны давать разный вариант,
        # но обязаны давать разный бакет-ключ. Косвенно проверяем через
        # совпадение назначений на всех парах сразу.
        if assign_variant(e1, x1, variants) == assign_variant(e2, x2, variants):
            collisions.append(((e1, x1), (e2, x2)))

    # При честном разделителе совпадения возможны случайно (~50% на пару),
    # поэтому проверяем строго: ключи должны различаться.
    from stats.randomization import _bucket_key  # noqa: WPS433

    for (e1, x1), (e2, x2) in pairs:
        assert _bucket_key(e1, x1) != _bucket_key(e2, x2), (
            f"Коллизия ключа хэширования: ({e1},{x1}) и ({e2},{x2}) дают один ключ. "
            f"entity_id и experiment_id склеиваются без разделителя."
        )


# --- 0.5 пограничные entity_id ----------------------------------------------

@pytest.mark.parametrize(
    "entity_id",
    [
        "",
        "a" * 10_000,
        "user@#$%^&*()<>?/\\|",
        "пользователь-42",
        "用户-42",
        "user\nid\twith\rwhitespace",
        "0",
        "-1",
        "null",
    ],
)
def test_0_5_edge_case_entity_ids(entity_id):
    """Пограничные entity_id не должны ронять hash-функцию."""
    variants = split_5050()
    vid = assign_variant(entity_id, 1, variants)
    assert vid in (1, 2), f"entity_id={entity_id!r} дал некорректный variant_id={vid}"


def test_0_5b_unicode_is_stable():
    """Кириллический entity_id назначается детерминированно."""
    variants = split_5050()
    first = assign_variant("ученик-Иванов", 3, variants)
    assert all(assign_variant("ученик-Иванов", 3, variants) == first for _ in range(20))


# --- дополнительно: корректность границ бакетов ------------------------------

def test_0_7_allocation_not_summing_to_100_is_rejected():
    """
    Если allocation_pct не суммируются в 100, бакетирование молча теряет трафик.
    Функция должна явно сигнализировать, а не отдавать последний вариант по умолчанию.
    """
    variants = [V(1, 30.0), V(2, 30.0)]  # сумма 60
    with pytest.raises(ValueError):
        assign_variant("user-1", 1, variants)


def test_0_8_empty_variants_raises():
    """Эксперимент без вариантов — явная ошибка, не IndexError."""
    with pytest.raises(ValueError):
        assign_variant("user-1", 1, [])
