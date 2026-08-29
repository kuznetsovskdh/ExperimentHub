"""
Сквозные проверки: полный путь от создания эксперимента до интерпретации,
изоляция экспериментов друг от друга и поведение под параллельной нагрузкой.
"""
import concurrent.futures
import time
import uuid

import httpx
import numpy as np
import pytest

from conftest import EH_BASE

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=EH_BASE, timeout=60.0) as c:
        r = c.get("/health")
        if r.status_code != 200 or r.json().get("database") != "ok":
            pytest.skip(f"Сервис или БД недоступны: {r.text}")
        yield c


def make_experiment(client, entity_type="user", split=(50.0, 50.0)):
    r = client.post("/experiments/", json={
        "name": f"e2e-{uuid.uuid4().hex[:8]}",
        "entity_type": entity_type,
        "variants": [
            {"name": "control", "allocation_pct": split[0]},
            {"name": "treatment", "allocation_pct": split[1]},
        ],
    })
    assert r.status_code == 200, r.text
    return r.json()


# --- полный пайплайн с известным эффектом -----------------------------------

@pytest.mark.slow
def test_e2e_known_effect_recovered_end_to_end():
    """
    Создать эксперимент → назначить 3000 сущностей → отправить события
    с заранее заданным эффектом → получить результат и убедиться, что
    посчитанный эффект согласуется с заложенным.
    """
    with httpx.Client(base_url=EH_BASE, timeout=120.0) as client:
        exp = make_experiment(client)
        exp_id = exp["id"]
        variant_by_name = {v["name"]: v["id"] for v in exp["variants"]}

        n = 3000
        base_rate, true_lift = 0.20, 0.05
        rng = np.random.default_rng(2024)

        assigned = {}
        for i in range(n):
            eid = f"e2e-{i}"
            r = client.get(f"/experiments/{exp_id}/assignment",
                           params={"entity_id": eid})
            assert r.status_code == 200, r.text
            assigned[eid] = r.json()["variant_name"]

        for eid, vname in assigned.items():
            p = base_rate + (true_lift if vname == "treatment" else 0.0)
            value = float(rng.random() < p)
            r = client.post(f"/experiments/{exp_id}/events", json={
                "entity_id": eid, "metric_name": "conversion",
                "metric_value": value, "event_key": f"{eid}-conv",
            })
            assert r.status_code == 200, r.text

        r = client.get(f"/experiments/{exp_id}/results", params={
            "metric_name": "conversion", "persist": True,
        })
        assert r.status_code == 200, r.text
        data = r.json()

        assert data["method"] == "z_test", f"Ожидался z_test для бинарной метрики: {data}"
        assert data["n_control"] + data["n_treatment"] == n
        assert abs(data["effect_size"] - true_lift) < 0.03, (
            f"Оценка эффекта {data['effect_size']} далеко от заложенного {true_lift}"
        )
        assert data["ci_lower"] < true_lift < data["ci_upper"], (
            f"CI [{data['ci_lower']}, {data['ci_upper']}] не накрывает истинный "
            f"эффект {true_lift}"
        )
        assert data["significant"], f"Эффект 5пп при n=3000 должен быть значим: {data}"
        assert not data["srm"]["srm_detected"], f"Ложный SRM: {data['srm']}"
        assert data["srm"]["reliable"] is True
        assert data.get("persisted") is True


@pytest.mark.slow
def test_e2e_aa_produces_no_effect():
    """Тот же пайплайн без реального эффекта не должен находить различий."""
    with httpx.Client(base_url=EH_BASE, timeout=120.0) as client:
        exp = make_experiment(client)
        exp_id = exp["id"]
        rng = np.random.default_rng(7)

        for i in range(2000):
            eid = f"aa-{i}"
            client.get(f"/experiments/{exp_id}/assignment", params={"entity_id": eid})
            client.post(f"/experiments/{exp_id}/events", json={
                "entity_id": eid, "metric_name": "conversion",
                "metric_value": float(rng.random() < 0.15),
                "event_key": f"{eid}-c",
            })

        r = client.get(f"/experiments/{exp_id}/results",
                       params={"metric_name": "conversion"})
        data = r.json()
        assert not data["significant"], (
            f"AA-тест нашёл эффект: p={data['p_value']}, effect={data['effect_size']}"
        )


# --- изоляция экспериментов --------------------------------------------------

def test_e2e_experiments_are_isolated(client):
    """
    Событие, отправленное в эксперимент A, не должно влиять на результаты
    эксперимента B, даже если entity_id совпадают.
    """
    exp_a = make_experiment(client, entity_type="user")
    exp_b = make_experiment(client, entity_type="sku")

    shared_ids = [f"shared-{i}" for i in range(30)]
    for eid in shared_ids:
        client.get(f"/experiments/{exp_a['id']}/assignment", params={"entity_id": eid})
        client.get(f"/experiments/{exp_b['id']}/assignment", params={"entity_id": eid})

    # События только в A.
    for eid in shared_ids:
        client.post(f"/experiments/{exp_a['id']}/events", json={
            "entity_id": eid, "metric_name": "m", "metric_value": 1.0,
        })

    r_b = client.get(f"/experiments/{exp_b['id']}/results",
                     params={"metric_name": "m", "fill_missing": 0})
    data_b = r_b.json()
    assert data_b["mean_control"] == 0.0 and data_b["mean_treatment"] == 0.0, (
        f"События эксперимента A протекли в B: {data_b}"
    )


def test_e2e_same_entity_different_variants_across_experiments(client):
    """
    Одна сущность в двух экспериментах может (и должна) получать
    независимые назначения — иначе эксперименты скоррелированы.
    """
    exp_a = make_experiment(client)
    exp_b = make_experiment(client)

    disagreements = 0
    n = 200
    for i in range(n):
        eid = f"iso-{i}"
        a = client.get(f"/experiments/{exp_a['id']}/assignment",
                       params={"entity_id": eid}).json()["variant_name"]
        b = client.get(f"/experiments/{exp_b['id']}/assignment",
                       params={"entity_id": eid}).json()["variant_name"]
        if a != b:
            disagreements += 1

    # При независимых назначениях расхождений ожидается ~50%.
    assert 0.3 * n < disagreements < 0.7 * n, (
        f"Назначения в двух экспериментах совпадают в "
        f"{(n - disagreements) / n:.1%} случаев — эксперименты скоррелированы"
    )


# --- конкурентность ---------------------------------------------------------

def test_e2e_concurrent_assignment_has_no_duplicates(client):
    """
    Параллельные запросы assignment для одной сущности должны вернуть
    один и тот же вариант и создать ровно одну запись назначения.
    Дубли назначений искажают SRM.
    """
    exp = make_experiment(client)
    exp_id = exp["id"]
    entity = "race-entity"

    def fetch(_):
        with httpx.Client(base_url=EH_BASE, timeout=30.0) as c:
            r = c.get(f"/experiments/{exp_id}/assignment",
                      params={"entity_id": entity})
            return r.status_code, r.json().get("variant_id")

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(fetch, range(32)))

    codes = {c for c, _ in results}
    variants = {v for _, v in results}
    assert codes == {200}, f"Не все параллельные запросы успешны: {codes}"
    assert len(variants) == 1, (
        f"Гонка дала разные варианты для одной сущности: {variants}"
    )

    # SRM должен видеть ровно одно назначение.
    r = client.get(f"/experiments/{exp_id}/results",
                   params={"metric_name": "nothing", "fill_missing": 0})
    if r.status_code == 200:
        assert r.json()["n_assigned_control"] + r.json()["n_assigned_treatment"] == 1


@pytest.mark.slow
def test_e2e_parallel_load_throughput():
    """
    Нагрузка на assignment несколькими параллельными клиентами.
    Печатает фактическую пропускную способность — цифру, которую
    честно можно указать в README.
    """
    with httpx.Client(base_url=EH_BASE, timeout=60.0) as setup:
        exp = make_experiment(setup)
    exp_id = exp["id"]

    total_requests = 600
    workers = 12

    def worker(idx):
        ok = 0
        with httpx.Client(base_url=EH_BASE, timeout=30.0) as c:
            for i in range(total_requests // workers):
                r = c.get(f"/experiments/{exp_id}/assignment",
                          params={"entity_id": f"load-{idx}-{i}"})
                if r.status_code == 200:
                    ok += 1
        return ok

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        oks = list(pool.map(worker, range(workers)))
    elapsed = time.perf_counter() - start

    succeeded = sum(oks)
    rps = succeeded / elapsed
    print(
        f"\nНагрузка assignment: {succeeded}/{total_requests} успешных за "
        f"{elapsed:.2f}с = {rps:.0f} req/s при {workers} параллельных клиентах"
    )
    assert succeeded == total_requests, f"Потеряно запросов: {total_requests - succeeded}"
