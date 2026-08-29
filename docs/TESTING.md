# Как протестировать ExperimentHub руками

Гайд для проверки сервиса целиком: бэкенд, интерфейс и обе интеграции.
Всё делается на локальном стеке, ничего внешнего не требуется.

---

## 0. Поднять стек

Сеть `eh_network` общая с rustest и salesguard — создаётся один раз:

```bash
docker network create eh_network      # если ещё нет
cd ~/experimenthub
docker compose up -d --build
```

Проверка, что всё поднялось:

```bash
curl -s localhost:8001/health          # {"status":"ok","database":"ok"}
curl -s -o /dev/null -w "%{http_code}\n" localhost:3002   # 200
```

| Адрес | Что там |
|---|---|
| http://localhost:3002 | интерфейс |
| http://localhost:8001/docs | документация API |
| http://localhost:8001/health | живость сервиса и БД |

Если порт занят — поменяйте `APP_PORT` / `FRONTEND_PORT` в `.env`.

---

## 1. Автотесты (2 минуты)

```bash
# быстрые — 122 теста
docker compose exec app python -m pytest -q -m "not slow"

# полный прогон с симуляциями — 147 тестов, ~10 минут
docker compose exec app python -m pytest -q

# один блок
docker compose exec app python -m pytest tests/test_block3_frequentist.py -q

# один тест
docker compose exec app python -m pytest -k test_3_5 -q
```

Тесты сгруппированы по проверяемому свойству, а не по файлам кода:

| Блок | Что доказывает |
|---|---|
| `test_block0_randomization` | деление детерминировано, равномерно на 100k, честно при 90/10, независимо между экспериментами |
| `test_block1_aa` | на данных без эффекта доля ложных срабатываний равна alpha |
| `test_block2_srm` | перекос ловится, на честных данных молчит, на малой выборке отказывается судить |
| `test_block3_frequentist` | p-value совпадает со scipy/statsmodels, вырожденные данные не роняют расчёт |
| `test_block4_cuped` | дисперсия падает на rho², оценка эффекта не смещается |
| `test_block5_bootstrap` | 95%-й интервал накрывает истину в 95% случаев |
| `test_block6_power` | рассчитанная выборка действительно даёт заявленную мощность |
| `test_block7_did` | эффект отделяется от тренда, нарушение параллельных трендов обнаруживается |
| `test_block8_events_api` | идемпотентность, события-сироты, жизненный цикл, латентность |
| `test_block9_multiple_testing` | Бонферрони и Беньямини—Хохберг сходятся со statsmodels |
| `test_block10_peeking` | измеряет, насколько подглядывание раздувает ошибку |
| `test_e2e_pipeline` | сквозной путь, изоляция экспериментов, гонки, нагрузка |

**Тесты интерфейса** (нужен запущенный `frontend`):

```bash
cd frontend && node uitest.mjs      # 49 проверок в 10 блоках
```

---

## 2. Пройти интерфейс глазами

Откройте http://localhost:3002 и пройдите по порядку.

### 2.1 Главная
- [ ] Заголовок раскрывается, точки в блоке ниже сыплются и делятся на две колонки
- [ ] Доли внизу анимации сходятся примерно к 50/50 — это работающая модель рандомизации, а не декорация
- [ ] Наведите на подчёркнутый пунктиром термин — появляется объяснение
- [ ] Переключите **«Объяснять просто»** в шапке — текст в подсказках меняется на точные формулировки

### 2.2 «Как сделать A/B» — главная страница для проверки
- [ ] Шесть шагов от гипотезы до решения
- [ ] На шаге 4 описано, как метрика была сломана и чем чинилась
- [ ] На шаге 5 — шкала доверительного интервала: столбик не пересекает вертикальную линию нуля
- [ ] Термины в тексте кликабельны и объясняют себя

### 2.3 Эксперименты → карточка
Откройте http://localhost:3002/experiments/2

- [ ] control 26,1%, treatment 57,1%, эффект +31,1 пп, p-value 0,0259
- [ ] Панель «проверка деления» показывает 45,1% / 54,9% и вердикт «перекоса нет»
- [ ] Внизу — предупреждения платформы про агрегацию и восполнение знаменателя

Теперь поиграйте с левой панелью — это главная проверка осмысленности:

| Что сделать | Что должно произойти |
|---|---|
| Снять галочку «Считать "нет события" за ноль» | Конверсия в обеих группах станет 100%, p-value = 1, появится предупреждение про вырожденность. Так эксперимент выглядел до починки |
| Сменить агрегацию на `count` | Метрика перестанет быть бинарной, метод переключится на t-тест |
| Поставить метод `z-тест` при агрегации `count` | Ошибка: z-тест применим только к 0/1 |
| Alpha 0,01 | Интервал станет шире, значимость может пропасть |
| Ввести несуществующую метрику | Понятное сообщение, а не пустой экран |
| Нажать «Остановить», потом «Возобновить» | Статус меняется, расчёт остаётся доступен |

### 2.4 Мастер создания
http://localhost:3002/new

- [ ] «Дальше» заблокирована, пока не введено имя
- [ ] На шаге 2 поставьте доли 30 и 50 — появится «должно быть ровно 100», переход заблокируется
- [ ] Полоса под вариантами показывает пропорцию деления
- [ ] На шаге 3 при конверсии 26,1% и MDE 10 пп — **336 на вариант**
- [ ] Создайте эксперимент — откроется его карточка

### 2.5 Расчёты
http://localhost:3002/tools

- [ ] Вкладка «До старта»: 26,1% и 10 пп → 336 на вариант, всего 672
- [ ] Кривая показывает, что при меньшем MDE выборка растёт нелинейно
- [ ] Введите конверсию 95 и MDE 20 — вместо падения объяснение, что так нельзя
- [ ] Вкладка «После»: n=25, конверсия 26,1%, эффект 31,1 → мощность 60,6% и предупреждение

### 2.6 Словарь
http://localhost:3002/glossary

- [ ] 21 термин, у каждого — простое объяснение, точное и типичная ошибка
- [ ] Поиск фильтрует
- [ ] Переключатель меняет, какая формулировка показана первой

### 2.7 Устойчивость
- [ ] Сузьте окно до ширины телефона — горизонтальной прокрутки нет, навигация переезжает вниз
- [ ] `docker compose stop app`, обновите страницу — появляется бейдж «демо-данные», цифры остаются настоящими
- [ ] `docker compose start app` — живые данные возвращаются

---

## 3. Проверить API напрямую

```bash
# создать эксперимент
curl -s -X POST localhost:8001/experiments/ -H 'Content-Type: application/json' -d '{
  "name":"manual-check","entity_type":"user",
  "variants":[{"name":"control","allocation_pct":50},{"name":"treatment","allocation_pct":50}]
}'

# назначить вариант (повторный вызов обязан вернуть тот же)
curl -s "localhost:8001/experiments/3/assignment?entity_id=user-1"
curl -s "localhost:8001/experiments/3/assignment?entity_id=user-1"

# отправить метрику; повтор с тем же event_key не должен задваивать
curl -s -X POST localhost:8001/experiments/3/events -H 'Content-Type: application/json' \
  -d '{"entity_id":"user-1","metric_name":"conv","metric_value":1.0,"event_key":"e-1"}'
curl -s -X POST localhost:8001/experiments/3/events -H 'Content-Type: application/json' \
  -d '{"entity_id":"user-1","metric_name":"conv","metric_value":1.0,"event_key":"e-1"}'
# → {"status":"duplicate_ignored", ...}

# результаты
curl -s "localhost:8001/experiments/3/results?metric_name=conv&fill_missing=0"

# калькуляторы
curl -s "localhost:8001/stats/sample-size?baseline_rate=0.261&mde=0.10"
curl -s "localhost:8001/stats/achieved-power?n=25&baseline_rate=0.261&observed_effect=0.3106"

# поправка на множественные сравнения
curl -s -X POST localhost:8001/stats/multiple-testing -H 'Content-Type: application/json' \
  -d '{"p_values":[0.001,0.008,0.02,0.03,0.04,0.2,0.5],"method":"benjamini_hochberg"}'
```

Что стоит попробовать сломать:

| Запрос | Ожидаемое поведение |
|---|---|
| Доли вариантов в сумме не 100 | 400 с объяснением |
| Один вариант | 400: нужно минимум два |
| Событие в остановленный эксперимент | 409 |
| `assignment` у остановленного | 400 |
| Событие от сущности без назначения | принимается, но помечается `assigned: false` |
| `metric_name`, которой нет | 400 «недостаточно данных» |

---

## 4. Подключить свой продукт

Полное руководство — [INTEGRATION.md](INTEGRATION.md): сетевая связность через
`eh_network`, код на Python и Node, отдача варианта на фронтенд, отправка
метрики с нулями, частые ошибки и чек-лист перед запуском.

Быстрая проверка, что связность есть, изнутри контейнера вашего продукта:

```bash
docker compose exec ваш-сервис python -c \
  "import urllib.request,json; print(json.load(urllib.request.urlopen('http://experimenthub-app-1:8000/health')))"
```

В интерфейсе инструкция подставляется автоматически: откройте карточку
эксперимента, в который ещё не приходили данные, — вместо ошибки там будет
готовый `docker-compose.yml` и код с подставленным id эксперимента.

---

## 5. Проверить интеграцию с РусТестом

Стек РусТеста должен быть поднят и подключён к `eh_network`.

```bash
cd ~/projects/rustest
SECRET=$(grep '^JWT_SECRET=' .env | cut -d= -f2-)
TOKEN=$(docker compose exec -T result-service python -c "
from jose import jwt; print(jwt.encode({'sub':'999','role':'user'}, '$SECRET', algorithm='HS256'))" | tr -d '\r\n')

# старт попытки — должен вернуть вариант и записать ноль в знаменатель
curl -s -X POST localhost:8003/attempts/start -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"test_id":2}'

# завершение — записывает единицу
curl -s -X POST localhost:8003/attempts/<ID>/finish -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"answers":[{"question_id":1,"selected_option_id":1,"is_correct":true}]}'

# что попало в ExperimentHub
cd ~/experimenthub
docker compose exec -T postgres psql -U eh_user -d experimenthub \
  -c "select entity_id, metric_value, event_key from events where entity_id='999' order by id;"
```

Ожидается ровно две строки: `0` с ключом `attempt-N-start` и `1` с `attempt-N-finish`.
Повторный вызов `finish` не должен добавлять третью — это защита от задвоения.

**Уберите за собой**, чтобы не портить реальный эксперимент:

```bash
docker compose exec -T postgres psql -U eh_user -d experimenthub -c "
delete from events where experiment_id=2 and entity_id='999';
delete from assignments where experiment_id=2 and entity_id='999';"
```

---

## 6. Проверить DiD на данных SalesGuard

БД SalesGuard должна быть в сети `eh_network` (прописано в её `docker-compose.yml`).

```bash
cd ~/experimenthub

# placebo: акции не было — эффекта быть не должно
docker compose exec -T -e SG_DB_HOST=salesguard-db-1 -e EH_BASE_URL=http://localhost:8000 app \
  python clients/salesguard_client.py --mode placebo --upload-id 221 --n-treatment 300 --n-control 300

# synthetic: заложен эффект +15% — метод обязан его найти
docker compose exec -T -e SG_DB_HOST=salesguard-db-1 -e EH_BASE_URL=http://localhost:8000 app \
  python clients/salesguard_client.py --mode synthetic --lift 0.15 --upload-id 221 --n-treatment 300 --n-control 300
```

Ожидается: в placebo `Значимо: НЕТ`, в synthetic `Значимо: ДА` с оценкой около +281 руб/день
при заложенных +334 (разница равна смещению, которое показал placebo).

Попробуйте `--n-treatment 20` — на 20 SKU тот же эффект перестаёт детектироваться.
Это и есть практический нижний предел размера treatment-группы.

---

## 7. Нагрузка

```bash
docker compose exec app python -m pytest tests/test_e2e_pipeline.py -q -s -m slow
```

Печатает фактическую пропускную способность. На dev-конфигурации (один воркер
uvicorn с `--reload`) получалось ~218 запросов в секунду при 12 параллельных
клиентах без потерь, медиана ответа 46 мс.

---

## Что сервис сознательно не делает

Это ограничения, а не недоделки — знать их важнее, чем обходить.

- **Не защищает от подглядывания.** Sequential testing не реализован. Платформа измеряет
  вред (30 ежедневных проверок → 26,8% ложных открытий вместо 5%) и предупреждает, но
  технически не мешает. Считайте выборку заранее.
- **Не знает, сколько метрик вы проверили.** `/results` считает одну за вызов; поправку
  применяйте через `/stats/multiple-testing`.
- **Не доказывает применимость DiD.** Проверка параллельных трендов может лишь не
  найти противоречия — это не то же самое, что подтверждение.
- **Сравнивает ровно два варианта.** Для многорукого эксперимента — попарно с поправкой.
