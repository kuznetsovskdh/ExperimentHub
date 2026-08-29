"""
Интеграция РусТеста с ExperimentHub — эталонный пример клиентского вызова.

Гипотеза эксперимента: подсказка о структуре теста, показанная перед первым
вопросом, увеличивает долю доведённых до конца попыток (completion rate).

Единица эксперимента — пользователь (entity_id = user_id). ExperimentHub
не знает, что это пользователь LMS: для него это произвольная строка.

Боевая реализация живёт в rustest/services/result-service/app/main.py;
здесь та же логика без зависимостей от кода РусТеста.
"""
import requests

EH_BASE = "http://localhost:8001"
EXPERIMENT_ID = 2
TIMEOUT = 2  # ExperimentHub не должен задерживать пользовательский flow


def get_variant(user_id: str) -> dict:
    """
    Вариант для пользователя при входе в тест.

    При недоступности ExperimentHub возвращается пустой словарь, и клиент
    показывает контрольный вариант: эксперимент пострадает, пользователь — нет.
    """
    try:
        r = requests.get(
            f"{EH_BASE}/experiments/{EXPERIMENT_ID}/assignment",
            params={"entity_id": str(user_id)},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return {}


def record_completion(user_id: str, attempt_id: int, completed: bool):
    """
    Записать метрику completion.

    Вызывается ДВАЖДЫ за попытку: с completed=False при старте и с
    completed=True при завершении. Ноль обязателен — без него в платформу
    попадают только успехи, знаменатель конверсии состоит из одних
    завершивших, и completion rate равна 100% в обеих группах независимо
    от варианта. Именно так выглядела первая версия этой интеграции.

    event_key делает вызов идемпотентным: повтор при сетевом retry не
    задваивает метрику.
    """
    stage = "finish" if completed else "start"
    try:
        requests.post(
            f"{EH_BASE}/experiments/{EXPERIMENT_ID}/events",
            json={
                "entity_id": str(user_id),
                "metric_name": "completion",
                "metric_value": 1.0 if completed else 0.0,
                "event_key": f"attempt-{attempt_id}-{stage}",
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        pass


def fetch_results(metric_name: str = "completion") -> dict:
    """
    Итог эксперимента.

    aggregation=max сводит несколько попыток одного пользователя к «завершил
    хотя бы раз». fill_missing здесь не нужен: ноль пишется явно при старте.
    """
    r = requests.get(
        f"{EH_BASE}/experiments/{EXPERIMENT_ID}/results",
        params={"metric_name": metric_name, "aggregation": "max"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    # Демонстрация полного цикла для одного пользователя.
    user_id = "demo-user-1"
    attempt_id = 999

    variant = get_variant(user_id)
    print("Назначенный вариант:", variant)

    record_completion(user_id, attempt_id, completed=False)  # начал
    record_completion(user_id, attempt_id, completed=True)   # завершил

    try:
        result = fetch_results()
        print(f"\nconversion control:   {result['mean_control']:.1%} "
              f"(n={result['n_control']})")
        print(f"conversion treatment: {result['mean_treatment']:.1%} "
              f"(n={result['n_treatment']})")
        print(f"эффект {result['effect_size']:+.4f}, p={result['p_value']}, "
              f"значимо: {result['significant']}")
        for w in result.get("warnings", []):
            print(" -", w)
    except requests.RequestException as e:
        print("Результаты недоступны:", e)
