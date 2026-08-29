"""
Hash-based назначение вариантов.

Детерминированное: один entity_id в одном эксперименте всегда получает
один и тот же вариант, без обращения к хранилищу.
"""
import hashlib

# Разрешение бакетов. 10000 вместо 100 — чтобы дробные allocation_pct
# (например 12.5%) отрабатывали точно, а не округлялись до целых процентов.
BUCKETS = 10_000

_ALLOCATION_TOLERANCE = 0.01


def _bucket_key(entity_id: str, experiment_id: int) -> str:
    """
    Ключ хэширования.

    Разделитель обязателен: без него ("1", 12) и ("11", 2) склеиваются
    в одну строку "112" и получают одинаковый бакет — назначения двух разных
    экспериментов оказываются скоррелированы.
    """
    return f"{entity_id}\x00{experiment_id}"


def bucket_of(entity_id: str, experiment_id: int) -> int:
    """Номер бакета сущности в диапазоне [0, BUCKETS)."""
    digest = hashlib.md5(_bucket_key(entity_id, experiment_id).encode("utf-8")).hexdigest()
    return int(digest, 16) % BUCKETS


def assign_variant(entity_id: str, experiment_id: int, variants: list) -> int:
    """
    Детерминированно назначает вариант по хэшу (entity_id, experiment_id).

    variants: объекты с полями id и allocation_pct. Порядок внутри функции
    задаётся сортировкой по id, чтобы назначения не зависели от порядка,
    в котором ORM вернула строки.
    """
    if not variants:
        raise ValueError(f"У эксперимента {experiment_id} нет вариантов")

    ordered = sorted(variants, key=lambda v: v.id)
    total = sum(v.allocation_pct for v in ordered)
    if abs(total - 100.0) > _ALLOCATION_TOLERANCE:
        raise ValueError(
            f"allocation_pct эксперимента {experiment_id} суммируются в {total}, а не в 100. "
            f"Часть трафика не была бы распределена."
        )

    bucket = bucket_of(entity_id, experiment_id)
    cumulative = 0.0
    for variant in ordered:
        cumulative += variant.allocation_pct
        if bucket < cumulative * BUCKETS / 100.0:
            return variant.id
    # Достижимо только из-за накопленной ошибки float на границе последнего варианта.
    return ordered[-1].id
