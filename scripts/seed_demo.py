"""
Демонстрационные эксперименты для витрины и скриншотов.

Каждый набор показывает одну грань платформы и подобран так, чтобы
результат был поучительным, а не просто «зелёным»:

  demo-checkout-hint    бинарная метрика, честный значимый эффект
  demo-cart-value       перекошенная выручка: t-тест и bootstrap расходятся
  demo-onboarding-cuped есть предэкспериментальные значения, CUPED сужает интервал
  demo-srm-broken       часть вызовов assignment не дошла — SRM обязан сработать

Данные синтетические и помечены префиксом demo-. Настоящий эксперимент в
базе один: rustest-hint-experiment.

Запуск:  docker compose exec app python scripts/seed_demo.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

import numpy as np
from sqlalchemy import text
from db import SessionLocal
from models import Assignment, Event, Experiment, Variant
from stats.randomization import assign_variant

DEMO_PREFIX = "demo-"


class V:
    def __init__(self, id, allocation_pct):
        self.id = id
        self.allocation_pct = allocation_pct


def drop_demo(session):
    ids = [r[0] for r in session.execute(
        text("SELECT id FROM experiments WHERE name LIKE :p"), {"p": DEMO_PREFIX + "%"}
    )]
    if not ids:
        return 0
    for t in ("results", "events", "assignments", "variants"):
        session.execute(text(f"DELETE FROM {t} WHERE experiment_id = ANY(:ids)"), {"ids": ids})
    session.execute(text("DELETE FROM experiments WHERE id = ANY(:ids)"), {"ids": ids})
    session.commit()
    return len(ids)


def create(session, name, entity_type, split=(50.0, 50.0)):
    exp = Experiment(name=name, entity_type=entity_type)
    session.add(exp)
    session.flush()
    variants = []
    for vname, pct in zip(("control", "treatment"), split):
        v = Variant(experiment_id=exp.id, name=vname, allocation_pct=pct)
        session.add(v)
        variants.append(v)
    session.commit()
    for v in variants:
        session.refresh(v)
    return exp, variants


def seed(session, exp, variants, n, value_fn, prefix, skip_fn=None):
    """
    Назначает сущности и пишет по одному событию на каждую.

    Вариант вычисляется той же функцией, что и в бою, поэтому распределение
    получается настоящим, а не расставленным вручную. skip_fn позволяет
    смоделировать потерю части назначений — так выглядит реальный SRM.
    """
    stand_ins = [V(v.id, v.allocation_pct) for v in variants]
    by_id = {v.id: v.name for v in variants}
    assignments, events = [], []

    for i in range(n):
        entity_id = f"{prefix}-{i}"
        vid = assign_variant(entity_id, exp.id, stand_ins)
        if skip_fn and skip_fn(by_id[vid], i):
            continue
        assignments.append(Assignment(experiment_id=exp.id, entity_id=entity_id, variant_id=vid))
        value, pre = value_fn(by_id[vid], i)
        events.append(Event(
            experiment_id=exp.id, entity_id=entity_id,
            metric_name=exp_metric[exp.id], metric_value=float(value),
            pre_period_value=None if pre is None else float(pre),
            event_key=f"{entity_id}-1",
        ))

    session.bulk_save_objects(assignments)
    session.bulk_save_objects(events)
    session.commit()
    return len(assignments)


exp_metric = {}

def main():
    session = SessionLocal()
    rng = np.random.default_rng(20260830)

    removed = drop_demo(session)
    if removed:
        print(f"убрано прежних демо-наборов: {removed}")

    # 1. Классический AB на конверсии. Эффект реальный, но скромный —
    #    именно такие и приходится измерять в жизни.
    exp, vs = create(session, "demo-checkout-hint", "user")
    exp_metric[exp.id] = "purchase"
    n = seed(session, exp, vs, 5200,
             lambda v, i: (1.0 if rng.random() < (0.121 if v == "control" else 0.145) else 0.0, None),
             "u")
    print(f"#{exp.id} demo-checkout-hint — {n} пользователей, конверсия покупки")

    # 2. Выручка с тяжёлым хвостом: редкие крупные заказы. Здесь параметрический
    #    интервал и bootstrap расходятся — ради этого bootstrap и нужен.
    exp, vs = create(session, "demo-cart-value", "user")
    exp_metric[exp.id] = "order_value"
    # Сильный хвост и умеренная выборка: именно в этом сочетании
    # параметрический интервал и bootstrap расходятся заметно.
    n = seed(session, exp, vs, 900,
             lambda v, i: (rng.lognormal(7.3 if v == "control" else 7.45, 1.9), None),
             "u")
    print(f"#{exp.id} demo-cart-value — {n} пользователей, средний чек")

    # 3. Метрика с историей: у каждого есть значение до эксперимента.
    #    Корреляция около 0.8 — CUPED заметно сужает интервал.
    exp, vs = create(session, "demo-onboarding-cuped", "user")
    exp_metric[exp.id] = "sessions_per_week"
    rho = 0.8
    noise = 3.0 * np.sqrt(1 - rho ** 2)

    def with_history(v, i):
        pre = rng.normal(9.0, 3.0)
        lift = 0.55 if v == "treatment" else 0.0
        post = rho * (pre - 9.0) + 9.0 + lift + rng.normal(0, noise)
        return post, pre

    n = seed(session, exp, vs, 1800, with_history, "u")
    print(f"#{exp.id} demo-onboarding-cuped — {n} пользователей, сессий в неделю + история")

    # 4. Сломанная рандомизация: часть вызовов assignment для treatment
    #    не дошла до платформы. Классическая причина SRM.
    exp, vs = create(session, "demo-srm-broken", "user")
    exp_metric[exp.id] = "activation"
    n = seed(session, exp, vs, 6000,
             lambda v, i: (1.0 if rng.random() < (0.30 if v == "control" else 0.335) else 0.0, None),
             "u",
             skip_fn=lambda variant, i: variant == "treatment" and rng.random() < 0.18)
    print(f"#{exp.id} demo-srm-broken — {n} сущностей, часть назначений потеряна")

    session.close()


if __name__ == "__main__":
    main()
