import * as React from "react";
import { api } from "@/lib/api";
import type { AchievedPower, SampleSize } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Term } from "@/components/Term";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { pct } from "@/lib/utils";

/**
 * Кривая «MDE → нужная выборка».
 *
 * Одна из самых полезных картинок в планировании: она показывает, что цена
 * чувствительности растёт нелинейно. Вдвое меньший эффект стоит вчетверо
 * большей выборки, и это видно глазами, а не выводится из формулы.
 */
function SampleSizeCurve({
  baseline,
  currentMde,
}: {
  baseline: number;
  currentMde: number;
}) {
  const points = React.useMemo(() => {
    const zA = 1.959964;
    const zB = 0.8416212;
    const p1 = baseline;
    const out: { mde: number; n: number }[] = [];
    for (let i = 1; i <= 60; i++) {
      const m = (i / 60) * 0.25;
      const p2 = p1 + m;
      if (p2 >= 1) break;
      const pool = (p1 + p2) / 2;
      const n =
        Math.pow(
          zA * Math.sqrt(2 * pool * (1 - pool)) +
            zB * Math.sqrt(p1 * (1 - p1) + p2 * (1 - p2)),
          2
        ) / Math.pow(m, 2);
      out.push({ mde: m, n: Math.ceil(n) });
    }
    return out;
  }, [baseline]);

  if (points.length === 0) return null;

  const maxN = Math.min(points[0].n, 60000);
  const W = 100;
  const H = 100;
  const x = (m: number) => (m / 0.25) * W;
  const y = (n: number) => H - (Math.min(n, maxN) / maxN) * H;

  const d = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${x(p.mde).toFixed(2)},${y(p.n).toFixed(2)}`)
    .join(" ");

  return (
    <div className="mt-6">
      <div className="eyebrow mb-3">цена чувствительности</div>
      <div className="relative h-40 w-full overflow-hidden rounded-lg border border-line-soft bg-ground">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="none"
          className="h-full w-full"
        >
          <path
            d={`${d} L${W},${H} L0,${H} Z`}
            fill="color-mix(in srgb, var(--treatment) 12%, transparent)"
          />
          <path
            d={d}
            fill="none"
            stroke="var(--treatment)"
            strokeWidth="0.8"
            vectorEffect="non-scaling-stroke"
          />
          {currentMde > 0 && currentMde <= 0.25 && (
            <line
              x1={x(currentMde)}
              y1="0"
              x2={x(currentMde)}
              y2={H}
              stroke="var(--control)"
              strokeWidth="0.8"
              strokeDasharray="3 3"
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>
        <span className="absolute bottom-1 left-2 font-mono text-[10px] text-faint">
          MDE 0
        </span>
        <span className="absolute bottom-1 right-2 font-mono text-[10px] text-faint">
          25 пп
        </span>
      </div>
      <p className="mt-2 text-[12px] leading-relaxed text-faint">
        Чем левее по шкале, тем дороже: чтобы поймать вдвое меньший эффект,
        нужно примерно вчетверо больше наблюдений.
      </p>
    </div>
  );
}

function Readout({
  label,
  value,
  hint,
  tone = "ink",
}: {
  label: React.ReactNode;
  value: string;
  hint?: string;
  tone?: "ink" | "good" | "warn" | "bad";
}) {
  const color =
    tone === "good"
      ? "text-good"
      : tone === "warn"
        ? "text-warn"
        : tone === "bad"
          ? "text-bad"
          : "text-ink";
  return (
    <div>
      <div className="eyebrow">{label}</div>
      <div className={`num mt-2 text-[clamp(28px,4.5vw,44px)] leading-none ${color}`}>
        {value}
      </div>
      {hint && <p className="mt-2 text-[12.5px] text-faint">{hint}</p>}
    </div>
  );
}

export default function Tools() {
  // Планирование
  const [baseline, setBaseline] = React.useState(26.1);
  const [mde, setMde] = React.useState(10);
  const [power, setPower] = React.useState(0.8);
  const [alpha, setAlpha] = React.useState(0.05);
  const [plan, setPlan] = React.useState<SampleSize | null>(null);

  // Постфактум
  const [n, setN] = React.useState(25);
  const [pBase, setPBase] = React.useState(26.1);
  const [effect, setEffect] = React.useState(31.1);
  const [achieved, setAchieved] = React.useState<AchievedPower | null>(null);

  React.useEffect(() => {
    const b = baseline / 100;
    const m = mde / 100;
    if (b <= 0 || b >= 1 || m <= 0 || b + m >= 1) return setPlan(null);
    api.sampleSize({ baseline_rate: b, mde: m, alpha, power }).then(setPlan).catch(() => setPlan(null));
  }, [baseline, mde, alpha, power]);

  React.useEffect(() => {
    const b = pBase / 100;
    const e = effect / 100;
    if (n <= 0 || b <= 0 || b >= 1 || b + e > 1 || b + e < 0)
      return setAchieved(null);
    api
      .achievedPower({ n, baseline_rate: b, observed_effect: e })
      .then(setAchieved)
      .catch(() => setAchieved(null));
  }, [n, pBase, effect]);

  return (
    <div className="mx-auto max-w-[1000px] px-5 pb-24 pt-16">
      <p className="eyebrow">расчёты</p>
      <h1 className="display mt-5 text-[clamp(32px,5vw,58px)] font-extrabold">
        Сколько нужно данных
      </h1>
      <p className="mt-6 max-w-[60ch] text-[16px] leading-relaxed text-muted">
        Два вопроса, которые задают до эксперимента и после. Сколько собирать,
        чтобы что-то увидеть, — и что означал результат, если ничего не нашли.
      </p>

      <Tabs defaultValue="plan" className="mt-10">
        <TabsList>
          <TabsTrigger value="plan">До старта</TabsTrigger>
          <TabsTrigger value="after">После</TabsTrigger>
        </TabsList>

        {/* ── Планирование ── */}
        <TabsContent value="plan" className="mt-7">
          <div className="grid gap-7 md:grid-cols-[1fr_1.1fr]">
            <Card>
              <CardContent className="space-y-5 pt-6">
                <label className="block">
                  <span className="mb-2 block text-[14px]">
                    Текущая конверсия, %
                  </span>
                  <Input
                    type="number"
                    className="num"
                    value={baseline}
                    step={0.1}
                    onChange={(e) => setBaseline(Number(e.target.value))}
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-[14px]">
                    <Term id="mde">MDE</Term>, пп
                  </span>
                  <Input
                    type="number"
                    className="num"
                    value={mde}
                    step={0.1}
                    onChange={(e) => setMde(Number(e.target.value))}
                  />
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <label className="block">
                    <span className="mb-2 block text-[14px]">
                      <Term id="power">Мощность</Term>
                    </span>
                    <Select
                      value={String(power)}
                      onChange={(e) => setPower(Number(e.target.value))}
                    >
                      <option value="0.8">0,80</option>
                      <option value="0.9">0,90</option>
                      <option value="0.95">0,95</option>
                    </Select>
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-[14px]">
                      <Term id="alpha">Alpha</Term>
                    </span>
                    <Select
                      value={String(alpha)}
                      onChange={(e) => setAlpha(Number(e.target.value))}
                    >
                      <option value="0.05">0,05</option>
                      <option value="0.01">0,01</option>
                      <option value="0.1">0,10</option>
                    </Select>
                  </label>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                {plan ? (
                  <>
                    <Readout
                      label="на каждый вариант"
                      value={plan.sample_size_per_variant.toLocaleString("ru")}
                      hint={`всего ${plan.sample_size_total.toLocaleString("ru")} наблюдений`}
                    />
                    <SampleSizeCurve
                      baseline={baseline / 100}
                      currentMde={mde / 100}
                    />
                  </>
                ) : (
                  <p className="text-[14px] text-muted">
                    Конверсия и конверсия плюс MDE должны лежать между 0 и 100%.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ── Постфактум ── */}
        <TabsContent value="after" className="mt-7">
          <div className="grid gap-7 md:grid-cols-[1fr_1.1fr]">
            <Card>
              <CardContent className="space-y-5 pt-6">
                <label className="block">
                  <span className="mb-2 block text-[14px]">
                    Наблюдений на вариант
                  </span>
                  <Input
                    type="number"
                    className="num"
                    value={n}
                    onChange={(e) => setN(Number(e.target.value))}
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-[14px]">
                    Конверсия контроля, %
                  </span>
                  <Input
                    type="number"
                    className="num"
                    value={pBase}
                    step={0.1}
                    onChange={(e) => setPBase(Number(e.target.value))}
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-[14px]">
                    Наблюдённый эффект, пп
                  </span>
                  <Input
                    type="number"
                    className="num"
                    value={effect}
                    step={0.1}
                    onChange={(e) => setEffect(Number(e.target.value))}
                  />
                </label>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                {achieved ? (
                  <>
                    <Readout
                      label={<Term id="power">достигнутая мощность</Term>}
                      value={pct(achieved.achieved_power)}
                      tone={
                        achieved.achieved_power >= 0.8
                          ? "good"
                          : achieved.achieved_power >= 0.5
                            ? "warn"
                            : "bad"
                      }
                    />
                    <p className="mt-5 max-w-[46ch] text-[14px] leading-relaxed text-muted">
                      {achieved.achieved_power >= 0.8
                        ? "Выборки хватало: если бы эффект такого размера был, вы бы его почти наверняка увидели."
                        : achieved.achieved_power >= 0.5
                          ? "Выборки было маловато. Значимый результат при такой мощности систематически завышает величину эффекта, а незначимый — почти ничего не доказывает."
                          : "Выборки категорически не хватало. При такой мощности отсутствие находки не говорит ни о чём: эффект мог быть и остаться незамеченным."}
                    </p>
                    {achieved.warnings.map((w, i) => (
                      <p
                        key={i}
                        className="mt-4 border-l-2 border-warn/60 pl-3 text-[13px] text-warn/90"
                      >
                        {w}
                      </p>
                    ))}
                  </>
                ) : (
                  <p className="text-[14px] text-muted">
                    Проверьте параметры: конверсия и конверсия плюс эффект
                    должны лежать между 0 и 100%.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
