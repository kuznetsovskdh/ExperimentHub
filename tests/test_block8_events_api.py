"""
Блок 8. Events API и жизненный цикл эксперимента (живой сервис + БД).

Запускается внутри контейнера app:
    docker compose exec app python -m pytest tests/test_block8_events_api.py
"""
import time
import uuid

import httpx
import pytest

from conftest import EH_BASE

pytestmark = pytest.mark.live

CLIENT_TIMEOUT = 30.0


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=EH_BASE, timeout=CLIENT_TIMEOUT) as c:
        r = c.get("/health")
        if r.status_code != 200 or r.json().get("database") != "ok":
            pytest.skip(f"Сервис или БД недоступны: {r.text}")
        yield c


def make_experiment(client, name=None, split=(50.0, 50.0), entity_type="user"):
    payload = {
        "name": name or f"test-{uuid.uuid4().hex[:8]}",
        "entity_type": entity_type,
        "variants": [
            {"name": "control", "allocation_pct": split[0]},
            {"name": "treatment", "allocation_pct": split[1]},
        ],
    }
    r = client.post("/experiments/", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# --- 8.1 идемпотентность ----------------------------------------------------

def test_8_1_duplicate_event_with_key_is_ignored(client):
    """Повтор события с тем же event_key не должен задваивать метрику."""
    exp = make_experiment(client)
    eid = "user-1"
    client.get(f"/experiments/{exp['id']}/assignment", params={"entity_id": eid})

    body = {
        "entity_id": eid,
        "metric_name": "completion",
        "metric_value": 1.0,
        "event_key": f"attempt-777-completion",
    }
    first = client.post(f"/experiments/{exp['id']}/events", json=body)
    second = client.post(f"/experiments/{exp['id']}/events", json=body)
    third = client.post(f"/experiments/{exp['id']}/events", json=body)

    assert first.json()["status"] == "ok", first.text
    assert second.json()["status"] == "duplicate_ignored", second.text
    assert third.json()["status"] == "duplicate_ignored", third.text


def test_8_1b_different_keys_are_both_recorded(client):
    """Разные event_key — разные события, дедупликация не должна их склеить."""
    exp = make_experiment(client)
    eid = "user-1"
    client.get(f"/experiments/{exp['id']}/assignment", params={"entity_id": eid})

    for key in ("attempt-1", "attempt-2"):
        r = client.post(f"/experiments/{exp['id']}/events", json={
            "entity_id": eid, "metric_name": "score",
            "metric_value": 1.0, "event_key": key,
        })
        assert r.json()["status"] == "ok", r.text


def test_8_1c_multiple_events_aggregate_to_one_observation(client):
    """
    Даже без event_key несколько событий одной сущности должны сводиться
    к одному наблюдению — иначе конверсия завышается за счёт активных
    пользователей, проходящих тест повторно.
    """
    exp = make_experiment(client)
    n_entities = 20
    for i in range(n_entities):
        eid = f"user-{i}"
        client.get(f"/experiments/{exp['id']}/assignment", params={"entity_id": eid})
        # Каждая пятая сущность шлёт событие 5 раз — как entity 74 в проде RusTest.
        repeats = 5 if i % 5 == 0 else 1
        for _ in range(repeats):
            client.post(f"/experiments/{exp['id']}/events", json={
                "entity_id": eid, "metric_name": "completion", "metric_value": 1.0,
            })

    r = client.get(f"/experiments/{exp['id']}/results", params={
        "metric_name": "completion", "aggregation": "max", "fill_missing": 0,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["n_control"] + data["n_treatment"] == n_entities, (
        f"Ожидалось {n_entities} наблюдений по числу сущностей, получено "
        f"{data['n_control']}+{data['n_treatment']}: повторные события не свёрнуты"
    )


# --- 8.2 событие без назначения ---------------------------------------------

def test_8_2_event_without_assignment_is_flagged(client):
    """Событие от сущности без назначения принимается, но помечается."""
    exp = make_experiment(client)
    r = client.post(f"/experiments/{exp['id']}/events", json={
        "entity_id": "never-assigned", "metric_name": "completion", "metric_value": 1.0,
    })
    assert r.status_code == 200, r.text
    assert r.json()["assigned"] is False
    assert r.json()["warnings"], "Нет предупреждения об отсутствии назначения"


def test_8_2b_orphan_events_excluded_from_results(client):
    """Такие события не должны попадать в расчёт эффекта."""
    exp = make_experiment(client)
    n_assigned = 20
    for i in range(n_assigned):
        eid = f"user-{i}"
        client.get(f"/experiments/{exp['id']}/assignment", params={"entity_id": eid})
        client.post(f"/experiments/{exp['id']}/events", json={
            "entity_id": eid, "metric_name": "m", "metric_value": 1.0,
        })
    for i in range(50):
        client.post(f"/experiments/{exp['id']}/events", json={
            "entity_id": f"orphan-{i}", "metric_name": "m", "metric_value": 1.0,
        })

    r = client.get(f"/experiments/{exp['id']}/results", params={"metric_name": "m"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["n_control"] + data["n_treatment"] == n_assigned, (
        f"Сироты попали в расчёт: {data['n_control']}+{data['n_treatment']}"
    )
    assert any("без назначения" in w for w in data["warnings"])


# --- 8.3 остановленный эксперимент ------------------------------------------

def test_8_3_stopped_experiment_rejects_events(client):
    """После остановки события не принимаются."""
    exp = make_experiment(client)
    client.get(f"/experiments/{exp['id']}/assignment", params={"entity_id": "u1"})

    stop = client.post(f"/experiments/{exp['id']}/stop")
    assert stop.status_code == 200, stop.text
    assert stop.json()["status"] == "stopped"

    r = client.post(f"/experiments/{exp['id']}/events", json={
        "entity_id": "u1", "metric_name": "m", "metric_value": 1.0,
    })
    assert r.status_code == 409, f"Событие принято в остановленный эксперимент: {r.text}"


def test_8_3b_stopped_experiment_rejects_assignment(client):
    exp = make_experiment(client)
    client.post(f"/experiments/{exp['id']}/stop")
    r = client.get(f"/experiments/{exp['id']}/assignment", params={"entity_id": "u2"})
    assert r.status_code == 400


def test_8_3c_stopped_experiment_still_computes_results(client):
    """Остановка закрывает сбор данных, но не доступ к уже собранному."""
    exp = make_experiment(client)
    # 30, а не 10: при десяти случайный сплит иногда оставляет в группе
    # меньше двух наблюдений, и расчёт законно отказывается считать.
    for i in range(30):
        eid = f"u{i}"
        client.get(f"/experiments/{exp['id']}/assignment", params={"entity_id": eid})
        client.post(f"/experiments/{exp['id']}/events", json={
            "entity_id": eid, "metric_name": "m", "metric_value": float(i % 2),
        })
    client.post(f"/experiments/{exp['id']}/stop")

    r = client.get(f"/experiments/{exp['id']}/results", params={"metric_name": "m"})
    assert r.status_code == 200, r.text
    assert r.json()["experiment_status"] == "stopped"


def test_8_3d_double_stop_is_conflict(client):
    exp = make_experiment(client)
    client.post(f"/experiments/{exp['id']}/stop")
    assert client.post(f"/experiments/{exp['id']}/stop").status_code == 409


def test_8_3e_resume_restores_collection(client):
    exp = make_experiment(client)
    client.post(f"/experiments/{exp['id']}/stop")
    r = client.post(f"/experiments/{exp['id']}/resume")
    assert r.status_code == 200 and r.json()["status"] == "active"
    assert client.get(
        f"/experiments/{exp['id']}/assignment", params={"entity_id": "u9"}
    ).status_code == 200


# --- 8.4 производительность приёма событий ----------------------------------

def test_8_4_event_ingestion_latency(client):
    """
    Приём события не должен быть узким местом клиентского flow.
    Замеряем медиану и p95 на серии последовательных запросов.
    """
    exp = make_experiment(client)
    for i in range(50):
        client.get(f"/experiments/{exp['id']}/assignment", params={"entity_id": f"u{i}"})

    latencies = []
    for i in range(200):
        start = time.perf_counter()
        r = client.post(f"/experiments/{exp['id']}/events", json={
            "entity_id": f"u{i % 50}", "metric_name": "perf", "metric_value": 1.0,
        })
        latencies.append((time.perf_counter() - start) * 1000)
        assert r.status_code == 200

    latencies.sort()
    median = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    print(f"\nПриём событий: медиана={median:.1f}мс p95={p95:.1f}мс")
    assert p95 < 500, f"p95 приёма событий {p95:.1f}мс — слишком медленно для inline-вызова"


def test_8_4b_assignment_latency(client):
    """Assignment вызывается синхронно в пользовательском flow — он критичен."""
    exp = make_experiment(client)
    latencies = []
    for i in range(200):
        start = time.perf_counter()
        r = client.get(
            f"/experiments/{exp['id']}/assignment", params={"entity_id": f"perf-{i}"}
        )
        latencies.append((time.perf_counter() - start) * 1000)
        assert r.status_code == 200
    latencies.sort()
    median = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    print(f"\nAssignment: медиана={median:.1f}мс p95={p95:.1f}мс")
    assert p95 < 500, f"p95 assignment {p95:.1f}мс"


# --- валидация входа --------------------------------------------------------

def test_8_5_validation(client):
    exp = make_experiment(client)
    # пустой entity_id
    assert client.post(f"/experiments/{exp['id']}/events", json={
        "entity_id": "", "metric_name": "m", "metric_value": 1.0,
    }).status_code == 422
    # отсутствующая метрика
    assert client.post(f"/experiments/{exp['id']}/events", json={
        "entity_id": "u", "metric_name": "", "metric_value": 1.0,
    }).status_code == 422
    # несуществующий эксперимент
    assert client.post("/experiments/999999/events", json={
        "entity_id": "u", "metric_name": "m", "metric_value": 1.0,
    }).status_code == 404


def test_8_5b_experiment_creation_validation(client):
    """Сумма allocation_pct и уникальность имён проверяются на создании."""
    bad_sum = client.post("/experiments/", json={
        "name": "bad", "entity_type": "user",
        "variants": [
            {"name": "a", "allocation_pct": 30.0},
            {"name": "b", "allocation_pct": 30.0},
        ],
    })
    assert bad_sum.status_code == 400

    dup_names = client.post("/experiments/", json={
        "name": "dup", "entity_type": "user",
        "variants": [
            {"name": "a", "allocation_pct": 50.0},
            {"name": "a", "allocation_pct": 50.0},
        ],
    })
    assert dup_names.status_code == 400

    single = client.post("/experiments/", json={
        "name": "one", "entity_type": "user",
        "variants": [{"name": "a", "allocation_pct": 100.0}],
    })
    assert single.status_code == 400
