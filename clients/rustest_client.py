"""
Пример интеграции РусТеста с ExperimentHub.
Вызывается при показе варианта и при завершении теста.
"""
import requests

EH_BASE = "http://localhost:8001"
EXPERIMENT_ID = 1  # ID эксперимента в ExperimentHub

def get_variant(user_id: str) -> int:
    """Получить вариант для пользователя при входе в тест."""
    r = requests.get(f"{EH_BASE}/experiments/{EXPERIMENT_ID}/assignment",
                     params={"entity_id": user_id})
    return r.json()["variant_id"]

def record_completion(user_id: str, completed: bool):
    """Записать факт завершения теста как метрику."""
    requests.post(f"{EH_BASE}/experiments/{EXPERIMENT_ID}/events",
                  json={
                      "entity_id": user_id,
                      "metric_name": "completion",
                      "metric_value": 1.0 if completed else 0.0
                  })
