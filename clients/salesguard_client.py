"""
Интеграция SalesGuard → ExperimentHub: DiD-оценка эффекта акции на SKU.

Почему DiD, а не AB. В SalesGuard рандомизация физически невозможна:
акция назначается по бизнес-логике (маржинальность, остатки, договорённости
с площадкой), а не жребием. Нельзя «показать скидку половине товаров».
Поэтому эффект оценивается сравнением динамики товаров с акцией и
сопоставимых товаров без неё — за вычетом общего рыночного тренда.

Скрипт работает напрямую с БД SalesGuard (таблица sales), собирает дневные
ряды выручки и отправляет их в ExperimentHub через /quasi/did-panel.

Режимы:
  --mode placebo   акции не было; фиктивная дата разреза. DiD обязан НЕ найти
                   эффект. Проверяет, что метод не выдумывает результат
                   на реальном шуме и сезонности.
  --mode synthetic к реальным рядам treatment-группы после даты разреза
                   добавляется известный эффект. Проверяет, что метод
                   находит эффект заданной величины на реальных данных.
  --mode real      треатмент-SKU задаются явно через --treatment-skus.

Пример:
    python clients/salesguard_client.py --mode placebo --upload-id 221
    python clients/salesguard_client.py --mode synthetic --lift 0.15
"""
import argparse
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import date, datetime

EH_BASE = os.environ.get("EH_BASE_URL", "http://localhost:8001")

SG_DSN = {
    "host": os.environ.get("SG_DB_HOST", "localhost"),
    "port": int(os.environ.get("SG_DB_PORT", "5432")),
    "dbname": os.environ.get("SG_DB_NAME", "salesguard"),
    "user": os.environ.get("SG_DB_USER", "sguser"),
    "password": os.environ.get("SG_DB_PASSWORD", "sgpass"),
}


def fetch_daily_revenue(upload_id: int, skus=None):
    """{sku: {date: revenue}} — дневные ряды выручки из SalesGuard."""
    import psycopg2

    query = """
        SELECT product, sale_date, SUM(revenue)::float
        FROM sales
        WHERE upload_id = %s AND sale_date IS NOT NULL AND product IS NOT NULL
        GROUP BY product, sale_date
        ORDER BY product, sale_date
    """
    params = [upload_id]
    if skus:
        query = query.replace("AND product IS NOT NULL",
                              "AND product = ANY(%s)")
        params.append(list(skus))

    with psycopg2.connect(**SG_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    series = defaultdict(dict)
    for product, sale_date, revenue in rows:
        series[product][sale_date] = revenue
    return dict(series)


def calendar_range(series):
    """Общий календарный диапазон по всем SKU."""
    all_dates = [d for days in series.values() for d in days]
    return min(all_dates), max(all_dates)


def build_panel(series, cut_date, skus, lift=0.0, date_bounds=None):
    """
    Режет ряды на pre/post относительно даты вмешательства.

    Дни без продаж восполняются нулями. WB и Ozon не пишут строку за день,
    когда товар не продавался, поэтому «среднее по имеющимся дням» — это
    средняя выручка в дни продаж, а не средняя дневная выручка. Разница
    существенна: акция, поднимающая частоту продаж, без zero-fill выглядит
    как отсутствие эффекта.

    lift применяется мультипликативно к post-периоду — так моделируется
    акция, дающая относительный прирост выручки.
    """
    if date_bounds is None:
        date_bounds = calendar_range(series)
    start, end = date_bounds

    panel = {}
    for sku in skus:
        days = series.get(sku, {})
        pre, post = [], []
        current = start
        while current <= end:
            value = days.get(current, 0.0)
            if current < cut_date:
                pre.append(value)
            else:
                post.append(value * (1 + lift))
            current = date.fromordinal(current.toordinal() + 1)
        panel[sku] = {"pre": pre, "post": post}
    return panel


def pick_comparable_skus(series, n_treatment, n_control, min_days=60):
    """
    Отбирает treatment и control из SKU со схожим объёмом выручки.

    Сопоставимость по объёму — минимальное требование к control-группе:
    товар за 100 рублей в день и товар за 100 тысяч реагируют на рынок
    по-разному, и параллельность их трендов ожидать не приходится.
    """
    totals = {
        sku: sum(days.values())
        for sku, days in series.items()
        if len(days) >= min_days
    }
    if len(totals) < n_treatment + n_control:
        raise SystemExit(
            f"Недостаточно SKU с историей >= {min_days} дней: "
            f"найдено {len(totals)}, нужно {n_treatment + n_control}"
        )

    ranked = sorted(totals, key=totals.get, reverse=True)
    # Берём соседей по рангу выручки и чередуем, чтобы группы были
    # сопоставимы по объёму, а не «крупные против мелких».
    window = ranked[: (n_treatment + n_control) * 2]
    treatment, control = [], []
    for i, sku in enumerate(window):
        if i % 2 == 0 and len(treatment) < n_treatment:
            treatment.append(sku)
        elif len(control) < n_control:
            control.append(sku)
        if len(treatment) == n_treatment and len(control) == n_control:
            break
    return treatment, control


def call_did_panel(treatment_panel, control_panel):
    body = json.dumps({
        "treatment": treatment_panel,
        "control": control_panel,
    }).encode()
    req = urllib.request.Request(
        f"{EH_BASE}/quasi/did-panel",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def report(res, mode, cut_date, lift):
    print(f"\n{'=' * 70}")
    print(f"DiD-оценка ({mode}), дата разреза: {cut_date}")
    print(f"{'=' * 70}")
    print(f"SKU в treatment: {res.get('n_treatment_entities')}, "
          f"control: {res.get('n_control_entities')}")
    print(f"Средняя дневная выручка treatment: "
          f"{res['mean_treatment_before']:.0f} → {res['mean_treatment_after']:.0f} "
          f"(Δ {res['delta_treatment']:+.0f})")
    print(f"Средняя дневная выручка control:   "
          f"{res['mean_control_before']:.0f} → {res['mean_control_after']:.0f} "
          f"(Δ {res['delta_control']:+.0f})")
    print()
    print(f"Чистый эффект (DiD): {res['did_effect']:+.1f} руб/день на SKU")
    if res.get("did_effect_pct_of_baseline") is not None:
        print(f"  в процентах от базы: {res['did_effect_pct_of_baseline']:+.2f}%")
    print(f"95% CI: [{res['ci_lower']:+.1f}, {res['ci_upper']:+.1f}]")
    print(f"p-value: {res['p_value']}")
    print(f"Значимо: {'ДА' if res['significant'] else 'НЕТ'}")

    pt = res["parallel_trends"]
    print(f"\nПараллельные тренды: "
          f"{'НАРУШЕНЫ' if pt.get('violated') else 'не отвергнуты'}", end="")
    if pt.get("testable"):
        print(f" (наклоны {pt['slope_treatment']:.2f} vs {pt['slope_control']:.2f}, "
              f"p={pt['p_value']})")
    else:
        print(" (не проверялись)")

    if res.get("warnings"):
        print("\nПредупреждения:")
        for w in res["warnings"]:
            print(f"  - {w}")

    print("\nИнтерпретация:")
    if mode == "placebo":
        if res["significant"]:
            print("  ПРОВАЛ placebo-теста: акции не было, но DiD нашёл эффект.")
            print("  Control-группа несопоставима либо метод даёт ложные срабатывания.")
        else:
            print("  Placebo-тест пройден: при отсутствии вмешательства эффект")
            print("  не обнаружен — метод не выдумывает результат на этих данных.")
    elif mode == "synthetic":
        expected = lift * res["mean_treatment_before"]
        print(f"  Заложенный эффект: {expected:+.1f} руб/день "
              f"({lift * 100:+.0f}% к базе)")
        covered = res["ci_lower"] <= expected <= res["ci_upper"]
        print(f"  Оценка {res['did_effect']:+.1f}, "
              f"{'CI накрывает истинное значение' if covered else 'CI НЕ накрывает истинное значение'}")


def main():
    p = argparse.ArgumentParser(description="DiD-анализ акции SalesGuard")
    p.add_argument("--mode", choices=["placebo", "synthetic", "real"],
                   default="placebo")
    p.add_argument("--upload-id", type=int, default=221)
    p.add_argument("--cut-date", default="2026-03-01",
                   help="Дата начала акции (YYYY-MM-DD)")
    p.add_argument("--lift", type=float, default=0.15,
                   help="Относительный эффект для режима synthetic")
    p.add_argument("--n-treatment", type=int, default=20)
    p.add_argument("--n-control", type=int, default=20)
    p.add_argument("--treatment-skus", nargs="*",
                   help="Явный список SKU с акцией (для режима real)")
    args = p.parse_args()

    cut_date = datetime.strptime(args.cut_date, "%Y-%m-%d").date()

    print(f"Загрузка рядов из SalesGuard (upload_id={args.upload_id})...")
    series = fetch_daily_revenue(args.upload_id)
    print(f"Загружено SKU: {len(series)}")

    if args.mode == "real":
        if not args.treatment_skus:
            raise SystemExit("Режим real требует --treatment-skus")
        treatment_skus = args.treatment_skus
        pool = [s for s in series if s not in set(treatment_skus)]
        _, control_skus = pick_comparable_skus(
            {s: series[s] for s in pool}, 0, args.n_control
        )
        lift = 0.0
    else:
        treatment_skus, control_skus = pick_comparable_skus(
            series, args.n_treatment, args.n_control
        )
        lift = args.lift if args.mode == "synthetic" else 0.0

    bounds = calendar_range(series)
    print(f"Календарный диапазон: {bounds[0]} — {bounds[1]} "
          f"(дни без продаж восполнены нулями)")
    treatment_panel = build_panel(series, cut_date, treatment_skus,
                                  lift=lift, date_bounds=bounds)
    control_panel = build_panel(series, cut_date, control_skus,
                                lift=0.0, date_bounds=bounds)

    res = call_did_panel(treatment_panel, control_panel)
    report(res, args.mode, cut_date, lift)


if __name__ == "__main__":
    main()
