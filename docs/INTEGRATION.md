# Как подключить свой продукт к A/B-тесту

Пошагово: от «есть сайт» до «вижу результат эксперимента». На примере
реальной интеграции РусТеста, которая уже работает.

ExperimentHub не знает ничего о вашем продукте. Он умеет две вещи: сказать,
какой вариант показать конкретной сущности, и принять число, которое вы
считаете метрикой. Всё остальное — ваша бизнес-логика.

```
ваш продукт                     ExperimentHub
     │
     │  1. кому что показать?
     ├────── GET /experiments/2/assignment?entity_id=42 ──────►
     ◄────── {"variant_name": "treatment"} ───────────────────┤
     │
     │  показывает нужную версию
     │
     │  2. вот что получилось
     ├────── POST /experiments/2/events ──────────────────────►
     │       {"entity_id":"42","metric_value":1.0}            │
     │                                                        │
     │  3. что вышло в итоге?
     ├────── GET /experiments/2/results?metric_name=... ──────►
     ◄────── эффект, p-value, интервал, предупреждения ───────┤
```

---

## Шаг 1. Сетевая связность

Выберите один из двух вариантов в зависимости от того, где живёт ваш продукт.

### Вариант А. Продукт в Docker — общая сеть

Так сделано в РусТесте. Контейнеры разных `docker compose` проектов видят
друг друга по имени сервиса, если состоят в одной внешней сети.

```bash
docker network create eh_network     # один раз на машину
```

В `docker-compose.yml` **вашего** продукта:

```yaml
services:
  your-backend:
    environment:
      EH_BASE_URL: http://experimenthub-app-1:8000
      EH_EXPERIMENT_ID: "2"
    networks:
      - eh_network          # плюс ваши обычные сети

networks:
  eh_network:
    external: true          # сеть создана снаружи, compose её не создаёт
```

Проверить связность изнутри вашего контейнера:

```bash
docker compose exec your-backend python -c \
  "import urllib.request,json; print(json.load(urllib.request.urlopen('http://experimenthub-app-1:8000/health')))"
# {'status': 'ok', 'database': 'ok'}
```

Если не резолвится — убедитесь, что оба проекта подключены к сети:

```bash
docker network inspect eh_network --format '{{range .Containers}}{{.Name}} {{end}}'
```

**Имя контейнера ExperimentHub** — `experimenthub-app-1`. Оно складывается из
имени папки проекта и имени сервиса; если папка называется иначе, посмотрите
фактическое имя через `docker ps`.

### Вариант Б. Продукт вне Docker

Обращайтесь по проброшенному порту:

```
EH_BASE_URL=http://localhost:8001
```

---

## Шаг 2. Создать эксперимент

Через интерфейс (`localhost:3002/new`) или запросом:

```bash
curl -s -X POST localhost:8001/experiments/ \
  -H 'Content-Type: application/json' -d '{
    "name": "checkout-button-color",
    "entity_type": "user",
    "variants": [
      {"name": "control",   "allocation_pct": 50},
      {"name": "treatment", "allocation_pct": 50}
    ]
  }'
```

Запомните `id` из ответа — он пойдёт в `EH_EXPERIMENT_ID`.

**`entity_type`** — что вы делите на группы. Это свободная строка: `user`,
`sku`, `session`, `store`. Правило одно: единица деления должна совпадать
с тем, на кого действует изменение. Если правку видит весь магазин целиком,
делить по пользователям нельзя — группы «протекут» друг в друга.

---

## Шаг 3. Спросить вариант

Вызывается в тот момент, когда вы собираетесь показать изменение.

**Ответ детерминирован**: один и тот же `entity_id` всегда получает один и тот
же вариант. Интерфейс не будет прыгать между визитами, кэшировать на своей
стороне не нужно.

### Python (requests)

```python
import requests

EH_BASE_URL = os.getenv("EH_BASE_URL", "http://experimenthub-app-1:8000")
EH_EXPERIMENT_ID = os.getenv("EH_EXPERIMENT_ID", "2")

def get_variant(user_id) -> str:
    """Вариант для пользователя. При недоступности сервиса — контроль."""
    try:
        r = requests.get(
            f"{EH_BASE_URL}/experiments/{EH_EXPERIMENT_ID}/assignment",
            params={"entity_id": str(user_id)},
            timeout=2,
        )
        r.raise_for_status()
        return r.json()["variant_name"]
    except requests.RequestException:
        return "control"
```

### Python без зависимостей (как в РусТесте)

```python
import urllib.request, json

def eh_get_variant(user_id: int) -> dict:
    try:
        url = f"{EH_BASE_URL}/experiments/{EH_EXPERIMENT_ID}/assignment?entity_id={user_id}"
        with urllib.request.urlopen(url, timeout=2) as r:
            return json.loads(r.read())
    except Exception:
        return {}
```

### Node.js

```javascript
async function getVariant(userId) {
  try {
    const r = await fetch(
      `${EH_BASE_URL}/experiments/${EH_EXPERIMENT_ID}/assignment?entity_id=${userId}`,
      { signal: AbortSignal.timeout(2000) }
    );
    if (!r.ok) throw new Error(r.status);
    return (await r.json()).variant_name;
  } catch {
    return "control";
  }
}
```

### Два правила, которые важнее кода

**Таймаут обязателен.** Вызов стоит в пользовательском пути. Две секунды —
разумный потолок; РусТест использует именно столько.

**Падать нельзя.** Если ExperimentHub недоступен, показывайте контрольный
вариант. Эксперимент пострадает — вы недосчитаетесь наблюдений, — но
пользователь не увидит ошибку. Оборачивайте вызов целиком.

---

## Шаг 4. Отдать вариант на фронтенд

Бэкенд возвращает вариант вместе с данными страницы, фронтенд решает, что
показать. В РусТесте это выглядит так:

```python
# result-service/app/main.py
@app.post("/attempts/start")
def start_attempt(...):
    attempt = Attempt(...)
    db.add(attempt); db.commit(); db.refresh(attempt)

    eh_data = eh_get_variant(user["id"])

    return {
        "id": attempt.id,
        ...,
        "eh_variant_name": eh_data.get("variant_name"),
    }
```

```jsx
// frontend/src/pages/TestPage.jsx
const [variant, setVariant] = useState(null);

const start = async () => {
  const { data } = await client.post("/attempts/start", { test_id: id });
  setVariant(data.eh_variant_name);
};

return variant === "treatment" ? <HintScreen /> : <FirstQuestion />;
```

Сравнивайте по **имени** варианта, а не по числовому `variant_id`: id
меняются при пересоздании эксперимента, имена — нет.

---

## Шаг 5. Присылать метрику

Здесь ломается большинство интеграций, поэтому подробно.

### Главное правило: событие с нулём тоже нужно

Если слать событие только при успехе, в платформу попадут одни успехи.
Знаменатель конверсии будет состоять из тех, у кого метрика сработала,
и конверсия окажется равна 100% в обеих группах независимо от варианта.

Именно так была сломана первая версия интеграции РусТеста: `/results`
возвращал 500, потому что при стопроцентной конверсии в обеих группах
дисперсия равна нулю и статистика не определена.

**Правильно:** ноль при входе в сценарий, единица при целевом действии.

```python
def record_metric(user_id, attempt_id, success: bool):
    try:
        requests.post(
            f"{EH_BASE_URL}/experiments/{EH_EXPERIMENT_ID}/events",
            json={
                "entity_id": str(user_id),
                "metric_name": "completion",
                "metric_value": 1.0 if success else 0.0,
                "event_key": f"attempt-{attempt_id}-{'finish' if success else 'start'}",
            },
            timeout=2,
        )
    except requests.RequestException:
        pass

# при старте попытки
record_metric(user_id, attempt.id, success=False)

# при завершении
record_metric(user_id, attempt_id, success=True)
```

Альтернатива, если поставить ноль в код неудобно: слать только успехи, а при
расчёте передавать `fill_missing=0` — тогда платформа сама посчитает нулями
всех назначенных без событий. Явный ноль надёжнее: он различает «пользователь
вошёл в сценарий» и «пользователю просто назначили вариант».

### event_key: защита от задвоения

Сеть моргнула, клиент повторил запрос — метрика удвоилась. `event_key`
делает отправку идемпотентной: повтор с тем же ключом вернёт
`{"status": "duplicate_ignored"}`.

Ключ должен быть стабильным и уникальным для события: `attempt-1234-finish`,
`order-5678-paid`. Не используйте время или случайное число.

### Несколько событий от одной сущности

Пользователь прошёл тест пять раз — пришло пять событий. Тесты предполагают
независимые наблюдения, поэтому при расчёте применяется агрегация: `max`
означает «засчитать успех, если он был хоть раз». Параметр задаётся в
интерфейсе или в запросе `/results`.

### Непрерывные метрики

Всё то же самое, просто значение не 0/1:

```python
json={
    "entity_id": str(user_id),
    "metric_name": "order_value",
    "metric_value": 4350.0,
    "pre_period_value": 3900.0,   # для CUPED, если есть история
}
```

`pre_period_value` — та же метрика **до** эксперимента. Если передать её для
всех сущностей, можно включить CUPED и получить более узкий интервал на той
же выборке.

---

## Шаг 6. Посмотреть результат

В интерфейсе: `localhost:3002/experiments/<id>`.

Запросом:

```bash
curl -s "localhost:8001/experiments/2/results?metric_name=completion&aggregation=max&fill_missing=0"
```

Параметры, которые меняют смысл ответа:

| Параметр | Зачем |
|---|---|
| `aggregation` | как свести несколько событий одной сущности к одному наблюдению |
| `fill_missing=0` | считать назначенных без событий нулями — обязательно для конверсий |
| `method` | `auto`, `z_test`, `t_test`, `bootstrap` |
| `use_cuped` | применить CUPED, если у всех есть `pre_period_value` |
| `alpha` | порог значимости |

Читайте не только `p_value`, но и:
- `srm` — если `srm_detected: true`, результату доверять нельзя, пока не
  найдена причина перекоса;
- `warnings` — платформа сама сообщает, что делает вывод шатким;
- `ci_lower` / `ci_upper` — величина эффекта живёт здесь, а не в p-value.

---

## Полный пример: РусТест

Что именно было сделано в реальном проекте.

**Гипотеза.** Подсказка о структуре теста перед первым вопросом увеличит
долю доведённых до конца попыток.

**Единица.** Пользователь (`entity_type: "user"`), подсказку видит человек.

**Метрика.** `completion` — бинарная: попытка завершена или нет.

**Инфраструктура.** `rustest/docker-compose.yml`:

```yaml
  result-service:
    environment:
      EH_BASE_URL: http://experimenthub-app-1:8000
      EH_EXPERIMENT_ID: "2"
    networks:
      - eh_network

networks:
  eh_network:
    external: true
```

**Код.** Три точки в `services/result-service/app/main.py`:

1. `eh_get_variant()` и `eh_record_completion()` — обёртки над двумя запросами,
   обе через `urllib` с таймаутом 2 секунды и `try/except`, глотающим всё.
2. `start_attempt` — получает вариант, возвращает его во фронтенд и пишет
   `completion = 0`.
3. `finish_attempt` — пишет `completion = 1` с ключом `attempt-{id}-finish`.

**Фронтенд.** `TestPage.jsx` показывает экран-подсказку, если вариант —
treatment.

**Результат.** control 26,1% (6 из 23), treatment 57,1% (16 из 28),
эффект +31,1 пп, p = 0,026, интервал [+5,4; +56,7], SRM не обнаружен.
Достигнутая мощность 60,6% — направление эффекта установлено, величина нет.

---

## Частые ошибки

| Симптом | Причина | Решение |
|---|---|---|
| Конверсия 100% в обеих группах, `/results` жалуется на нулевую дисперсию | шлются только успехи | слать ноль при входе в сценарий или передавать `fill_missing=0` |
| Метрика задвоена, конверсия больше 100% | нет `event_key`, ретраи создают дубли | добавить стабильный `event_key` |
| «В эксперименте нет ни одного назначения» | продукт не вызывает `/assignment` либо не достучался | проверить сеть и `EH_BASE_URL` изнутри контейнера |
| SRM обнаружен | часть вызовов `/assignment` не доходит, либо вариант кэшируется на стороне продукта | не кэшировать назначение, проверить таймауты |
| `Connection refused` из контейнера | продукт не в сети `eh_network` | добавить сеть в compose и пересоздать контейнер |
| Событие отклонено с 409 | эксперимент остановлен | возобновить или создать новый |
| Пользователи видят разные варианты в разных визитах | продукт сам решает вариант при недоступности сервиса случайным образом | фолбэк всегда на контроль, не на случайный выбор |

---

## Чек-лист перед запуском

- [ ] Размер выборки посчитан заранее на `/tools`, дата окончания зафиксирована
- [ ] Оба вызова обёрнуты в таймаут и `try/except`, фолбэк — контроль
- [ ] Событие с нулём отправляется, либо расчёт идёт с `fill_missing=0`
- [ ] У событий есть `event_key`
- [ ] Проверено на тестовом `entity_id`, что повторный вызов даёт тот же вариант
- [ ] Понятно, что считать успехом и когда останавливаться
