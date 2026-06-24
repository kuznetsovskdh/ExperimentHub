import hashlib

def assign_variant(entity_id: str, experiment_id: int, variants: list) -> int:
    """
    Детерминированно назначает вариант по hash(entity_id + experiment_id).
    Возвращает variant_id.
    variants: список объектов с полями id, allocation_pct (отсортированных по id).
    """
    key = f"{entity_id}{experiment_id}"
    bucket = int(hashlib.md5(key.encode()).hexdigest(), 16) % 100
    cumulative = 0.0
    for variant in sorted(variants, key=lambda v: v.id):
        cumulative += variant.allocation_pct
        if bucket < cumulative:
            return variant.id
    return variants[-1].id
