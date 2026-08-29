import * as React from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Info, Pause, Play, TriangleAlert } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Experiment, ResultPayload } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Term } from "@/components/Term";
import { IntervalBar } from "@/components/IntervalBar";
import { IntegrationGuide } from "@/components/IntegrationGuide";
import { fmtP, num, pct, pp } from "@/lib/utils";

/** Подпись к управляющему параметру: что он меняет и почему это важно. */
function Field({
  label,
  hint,
  children,
}: {
  label: React.ReactNode;
  hint: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] text-ink">{label}</span>
      {children}
      <span className="mt-1.5 block text-[11.5px] leading-snug text-faint">
        {hint}
      </span>
    </label>
  );
}

export default function ExperimentDetail() {
  const { id } = useParams();
  const expId = Number(id);

  const [exp, setExp] = React.useState<Experiment | null>(null);
  const [result, setResult] = React.useState<ResultPayload | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  const [metric, setMetric] = React.useState("completion");
  const [method, setMethod] = React.useState("auto");
  const [aggregation, setAggregation] = React.useState("max");
  const [fillZero, setFillZero] = React.useState(true);
  const [useCuped, setUseCuped] = React.useState(false);
  const [alpha, setAlpha] = React.useState(0.05);

  React.useEffect(() => {
    api.getExperiment(expId).then(setExp).catch(() => undefined);
  }, [expId]);

  const load = React.useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .getResults(expId, {
        metric_name: metric,
        method,
        aggregation,
        fill_missing: fillZero ? 0 : null,
        use_cuped: useCuped,
        alpha,
      })
      .then((r) => {
        setResult(r);
        setError(null);
      })
      .catch((e) => {
        setResult(null);
        setError(e instanceof ApiError ? e.message : String(e));
      })
      .finally(() => setLoading(false));
  }, [expId, metric, method, aggregation, fillZero, useCuped, alpha]);

  React.useEffect(() => {
    load();
  }, [load]);

  // «Нет назначений» и «недостаточно данных» означают, что продукт ещё
  // не подключён, — это состояние онбординга, а не сбой.
  const needsIntegration =
    !!error && /нет ни одного назначения|Недостаточно данных/i.test(error);

  const toggleStatus = async () => {
    if (!exp) return;
    const next =
      exp.status === "active"
        ? await api.stopExperiment(exp.id)
        : await api.resumeExperiment(exp.id);
    setExp({ ...exp, ...next });
  };

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 pt-12">
      <Link
        to="/experiments"
        className="inline-flex items-center gap-2 text-[13px] text-muted transition-colors hover:text-ink"
      >
        <ArrowLeft className="size-3.5" />к экспериментам
      </Link>

      <header className="mt-7 flex flex-wrap items-start justify-between gap-6">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <span className="num text-[12px] text-faint">#{expId}</span>
            {exp && (
              <Badge variant={exp.status === "active" ? "good" : "default"}>
                {exp.status === "active" ? "активен" : "остановлен"}
              </Badge>
            )}
          </div>
          <h1 className="display mt-3 text-[clamp(28px,4.6vw,52px)] font-extrabold">
            {exp?.name ?? "Загрузка…"}
          </h1>
          {exp?.variants && (
            <div className="mt-4 flex flex-wrap gap-2">
              {exp.variants.map((v, i) => (
                <Badge key={v.id} variant={i === 0 ? "control" : "treatment"}>
                  {v.name} · {v.allocation_pct}%
                </Badge>
              ))}
            </div>
          )}
        </div>

        {exp && (
          <Button variant="outline" onClick={toggleStatus}>
            {exp.status === "active" ? (
              <>
                <Pause /> Остановить
              </>
            ) : (
              <>
                <Play /> Возобновить
              </>
            )}
          </Button>
        )}
      </header>

      <div className="mt-12 grid gap-8 lg:grid-cols-[300px_1fr]">
        {/* Управление расчётом */}
        <aside className="order-2 space-y-5 self-start rounded-xl border border-line-soft bg-surface p-5 lg:sticky lg:top-28 lg:order-1">
          <p className="eyebrow">как считать</p>

          <Field
            label="Метрика"
            hint="Имя, под которым продукт присылает события."
          >
            <Input
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              placeholder="completion"
            />
          </Field>

          <Field
            label={<Term id="aggregation">Агрегация</Term>}
            hint="Что делать, если от одной сущности пришло несколько событий."
          >
            <Select
              value={aggregation}
              onChange={(e) => setAggregation(e.target.value)}
            >
              <option value="max">max — успех, если был хоть раз</option>
              <option value="last">last — последнее значение</option>
              <option value="first">first — первое значение</option>
              <option value="mean">mean — среднее</option>
              <option value="sum">sum — сумма</option>
              <option value="count">count — число событий</option>
            </Select>
          </Field>

          <Field
            label="Метод"
            hint="«Авто» выбирает z-тест для метрик да/нет и t-тест для числовых."
          >
            <Select value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="auto">авто</option>
              <option value="z_test">z-тест — доли</option>
              <option value="t_test">t-тест Уэлча — числа</option>
              <option value="bootstrap">bootstrap — перекошенные данные</option>
            </Select>
          </Field>

          <Field
            label={<Term id="alpha">Alpha</Term>}
            hint="Порог значимости. Задаётся до эксперимента."
          >
            <Select
              value={String(alpha)}
              onChange={(e) => setAlpha(Number(e.target.value))}
            >
              <option value="0.05">0,05 — стандартно</option>
              <option value="0.01">0,01 — строже</option>
              <option value="0.1">0,10 — мягче</option>
            </Select>
          </Field>

          <div className="space-y-3 border-t border-line-soft pt-4">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={fillZero}
                onChange={(e) => setFillZero(e.target.checked)}
                className="mt-1 accent-[#ff6b3d]"
              />
              <span>
                <span className="block text-[13px] text-ink">
                  Считать «нет события» за ноль
                </span>
                <span className="mt-1 block text-[11.5px] leading-snug text-faint">
                  Обязательно для конверсий: иначе{" "}
                  <Term id="fill-missing">знаменатель</Term> состоит из одних
                  успехов.
                </span>
              </span>
            </label>

            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={useCuped}
                onChange={(e) => setUseCuped(e.target.checked)}
                className="mt-1 accent-[#ff6b3d]"
              />
              <span>
                <span className="block text-[13px] text-ink">
                  Применить <Term id="cuped">CUPED</Term>
                </span>
                <span className="mt-1 block text-[11.5px] leading-snug text-faint">
                  Нужны предэкспериментальные значения у всех сущностей.
                </span>
              </span>
            </label>
          </div>
        </aside>

        {/* Результат */}
        <div className="order-1 min-w-0 lg:order-2">
          {loading && !result && (
            <div className="h-[420px] animate-pulse rounded-xl border border-line-soft bg-surface" />
          )}

          {/* Для эксперимента, куда ещё не пришли данные, «нет назначений» —
              не ошибка, а следующий шаг работы. Показываем инструкцию
              по подключению продукта вместо сообщения о сбое. */}
          {error && needsIntegration && exp && (
            <IntegrationGuide
              experimentId={expId}
              entityType={exp.entity_type}
              variants={exp.variants ?? []}
            />
          )}

          {error && !needsIntegration && (
            <div className="rounded-xl border border-bad/30 bg-bad/5 p-6">
              <div className="flex items-start gap-3">
                <Info className="mt-0.5 size-4 shrink-0 text-bad" />
                <div>
                  <p className="font-medium text-ink">Расчёт невозможен</p>
                  <p className="mt-2 text-[14px] leading-relaxed text-muted">
                    {error}
                  </p>
                  <p className="mt-3 text-[13px] leading-relaxed text-faint">
                    Проверьте имя метрики и настройки слева — часть параметров
                    меняет требования к данным.
                  </p>
                </div>
              </div>
            </div>
          )}

          {result && !error && (
            <div className="space-y-6">
              {/* Две группы */}
              <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line-soft bg-line-soft">
                <div className="bg-surface p-6">
                  <div className="eyebrow !text-control">
                    {result.control_variant.name}
                  </div>
                  <div className="num mt-3 text-[clamp(28px,4vw,44px)] leading-none text-control">
                    {pct(result.mean_control)}
                  </div>
                  <p className="mt-2 text-[12px] text-faint">
                    {result.n_control} наблюдений из{" "}
                    {result.n_assigned_control} назначенных
                  </p>
                </div>
                <div className="bg-surface p-6">
                  <div className="eyebrow !text-treatment">
                    {result.treatment_variant.name}
                  </div>
                  <div className="num mt-3 text-[clamp(28px,4vw,44px)] leading-none text-treatment">
                    {pct(result.mean_treatment)}
                  </div>
                  <p className="mt-2 text-[12px] text-faint">
                    {result.n_treatment} наблюдений из{" "}
                    {result.n_assigned_treatment} назначенных
                  </p>
                </div>
              </div>

              {/* Интервал */}
              <div className="rounded-xl border border-line-soft bg-surface p-6">
                <div className="mb-6 flex flex-wrap items-baseline gap-x-8 gap-y-3">
                  <div>
                    <div className="eyebrow">
                      <Term id="effect-size">эффект</Term>
                    </div>
                    <div className="num mt-1.5 text-[30px] leading-none text-ink">
                      {pp(result.effect_size)}
                    </div>
                  </div>
                  <div>
                    <div className="eyebrow">
                      <Term id="p-value">p-value</Term>
                    </div>
                    <div
                      className={`num mt-1.5 text-[30px] leading-none ${
                        result.significant ? "text-good" : "text-muted"
                      }`}
                    >
                      {fmtP(result.p_value)}
                    </div>
                  </div>
                  <div>
                    <div className="eyebrow">метод</div>
                    <div className="num mt-1.5 text-[15px] text-muted">
                      {result.method}
                      {result.cuped?.applied && " + cuped"}
                    </div>
                  </div>
                </div>

                <IntervalBar
                  effect={result.effect_size}
                  lower={result.ci_lower}
                  upper={result.ci_upper}
                  significant={result.significant}
                />
              </div>

              {/* SRM */}
              <div className="rounded-xl border border-line-soft bg-surface p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <div className="eyebrow">
                      <Term id="srm">проверка деления</Term>
                    </div>
                    <p className="mt-2 text-[14px] text-muted">
                      Фактически{" "}
                      <span className="num text-control">
                        {num(result.srm.observed_ratio[0], 1)}%
                      </span>{" "}
                      /{" "}
                      <span className="num text-treatment">
                        {num(result.srm.observed_ratio[1], 1)}%
                      </span>{" "}
                      при заданных{" "}
                      <span className="num">
                        {result.srm.expected_ratio.map((v) => num(v, 0)).join(" / ")}%
                      </span>
                    </p>
                  </div>
                  <Badge
                    variant={
                      result.srm.srm_detected
                        ? "bad"
                        : result.srm.reliable
                          ? "good"
                          : "warn"
                    }
                  >
                    {result.srm.srm_detected
                      ? "обнаружен перекос"
                      : result.srm.reliable
                        ? "перекоса нет"
                        : "выборки мало для проверки"}
                  </Badge>
                </div>
              </div>

              {/* Предупреждения — то, ради чего бэкенд их и возвращает */}
              {result.warnings.length > 0 && (
                <div className="space-y-2">
                  <p className="eyebrow">на что обратить внимание</p>
                  {result.warnings.map((w, i) => (
                    <div
                      key={i}
                      className="flex gap-3 rounded-lg border border-warn/25 bg-warn/[0.04] p-4"
                    >
                      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warn" />
                      <p className="text-[13.5px] leading-relaxed text-muted">
                        {w}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
