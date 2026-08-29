import * as React from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Check } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { SampleSize } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Term } from "@/components/Term";

type VariantDraft = { name: string; allocation_pct: number };

const ENTITY_TYPES = [
  { value: "user", label: "пользователь — интерфейс, письма, обучение" },
  { value: "sku", label: "товар / SKU — цены, карточки, акции" },
  { value: "session", label: "сессия — разовые сценарии" },
  { value: "store", label: "магазин или регион — офлайн-изменения" },
];

export default function NewExperiment() {
  const navigate = useNavigate();
  const [step, setStep] = React.useState(0);

  const [name, setName] = React.useState("");
  const [entityType, setEntityType] = React.useState("user");
  const [variants, setVariants] = React.useState<VariantDraft[]>([
    { name: "control", allocation_pct: 50 },
    { name: "treatment", allocation_pct: 50 },
  ]);

  const [baseline, setBaseline] = React.useState(20);
  const [mde, setMde] = React.useState(5);
  const [plan, setPlan] = React.useState<SampleSize | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [creating, setCreating] = React.useState(false);

  const total = variants.reduce((s, v) => s + (v.allocation_pct || 0), 0);
  const sumOk = Math.abs(total - 100) < 0.01;
  const namesOk =
    variants.every((v) => v.name.trim().length > 0) &&
    new Set(variants.map((v) => v.name.trim())).size === variants.length;

  React.useEffect(() => {
    if (step !== 2) return;
    const b = baseline / 100;
    const m = mde / 100;
    if (b <= 0 || b >= 1 || m <= 0 || b + m >= 1) {
      setPlan(null);
      return;
    }
    api
      .sampleSize({ baseline_rate: b, mde: m })
      .then(setPlan)
      .catch(() => setPlan(null));
  }, [step, baseline, mde]);

  const create = async () => {
    setCreating(true);
    setError(null);
    try {
      const exp = await api.createExperiment({
        name: name.trim(),
        entity_type: entityType,
        variants: variants.map((v) => ({
          name: v.name.trim(),
          allocation_pct: v.allocation_pct,
        })),
      });
      navigate(`/experiments/${exp.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
      setCreating(false);
    }
  };

  const steps = ["Что проверяем", "Как делим", "Сколько собирать"];

  return (
    <div className="mx-auto max-w-[840px] px-5 pb-24 pt-16">
      <p className="eyebrow">новый эксперимент</p>
      <h1 className="display mt-5 text-[clamp(32px,5vw,58px)] font-extrabold">
        Собрать эксперимент
      </h1>

      {/* Шаги */}
      <div className="mt-10 flex gap-2">
        {steps.map((s, i) => (
          <button
            key={s}
            onClick={() => i < step && setStep(i)}
            disabled={i > step}
            className={`flex-1 border-t-2 pt-3 text-left transition-colors ${
              i === step
                ? "border-treatment text-ink"
                : i < step
                  ? "border-control text-muted hover:text-ink"
                  : "border-line-soft text-faint"
            }`}
          >
            <span className="num text-[11px]">0{i + 1}</span>
            <span className="mt-1 block text-[13px]">{s}</span>
          </button>
        ))}
      </div>

      <div className="mt-10">
        {/* ── Шаг 1 ── */}
        {step === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-7"
          >
            <label className="block">
              <span className="mb-2 block text-[15px] text-ink">
                Название эксперимента
              </span>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="например, hint-before-test"
                autoFocus
              />
              <span className="mt-2 block text-[12.5px] text-faint">
                Такое, чтобы через полгода вы поняли, что проверяли.
              </span>
            </label>

            <label className="block">
              <span className="mb-2 block text-[15px] text-ink">
                Кого делим на группы
              </span>
              <Select
                value={entityType}
                onChange={(e) => setEntityType(e.target.value)}
              >
                {ENTITY_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </Select>
              <span className="mt-2 block text-[12.5px] leading-relaxed text-faint">
                <Term id="entity-id">Единица деления</Term> должна совпадать с
                тем, на кого действует изменение. Если правку видит весь
                магазин, делить по пользователям нельзя — группы «протекут»
                друг в друга.
              </span>
            </label>

            <Button
              onClick={() => setStep(1)}
              disabled={name.trim().length === 0}
              size="lg"
            >
              Дальше
              <ArrowRight />
            </Button>
          </motion.div>
        )}

        {/* ── Шаг 2 ── */}
        {step === 1 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-7"
          >
            <div>
              <p className="mb-3 text-[15px] text-ink">
                Варианты и <Term id="allocation">доли трафика</Term>
              </p>
              <div className="space-y-3">
                {variants.map((v, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span
                      className={`size-2 shrink-0 rounded-full ${
                        i === 0 ? "bg-control" : "bg-treatment"
                      }`}
                    />
                    <Input
                      value={v.name}
                      onChange={(e) => {
                        const next = [...variants];
                        next[i] = { ...v, name: e.target.value };
                        setVariants(next);
                      }}
                      placeholder="имя варианта"
                    />
                    <div className="relative w-28 shrink-0">
                      <Input
                        type="number"
                        min={0}
                        max={100}
                        value={v.allocation_pct}
                        onChange={(e) => {
                          const next = [...variants];
                          next[i] = {
                            ...v,
                            allocation_pct: Number(e.target.value),
                          };
                          setVariants(next);
                        }}
                        className="num pr-7"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[13px] text-faint">
                        %
                      </span>
                    </div>
                    {variants.length > 2 && (
                      <button
                        onClick={() =>
                          setVariants(variants.filter((_, k) => k !== i))
                        }
                        className="shrink-0 px-2 text-[13px] text-faint transition-colors hover:text-bad"
                      >
                        убрать
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-4">
                <button
                  onClick={() =>
                    setVariants([
                      ...variants,
                      { name: `variant-${variants.length}`, allocation_pct: 0 },
                    ])
                  }
                  className="text-[13px] text-muted transition-colors hover:text-ink"
                >
                  + добавить вариант
                </button>
                <span
                  className={`num text-[13px] ${
                    sumOk ? "text-good" : "text-bad"
                  }`}
                >
                  сумма: {total}%{" "}
                  {sumOk ? "✓" : "— должно быть ровно 100"}
                </span>
              </div>

              {!namesOk && (
                <p className="mt-3 text-[13px] text-bad">
                  Имена вариантов должны быть заполнены и не повторяться.
                </p>
              )}
            </div>

            {/* Наглядная полоса деления */}
            <div className="flex h-3 overflow-hidden rounded-full border border-line-soft">
              {variants.map((v, i) => (
                <div
                  key={i}
                  style={{ width: `${Math.max(v.allocation_pct, 0)}%` }}
                  className={i === 0 ? "bg-control" : "bg-treatment"}
                />
              ))}
            </div>

            <div className="flex gap-3">
              <Button variant="ghost" onClick={() => setStep(0)}>
                Назад
              </Button>
              <Button
                onClick={() => setStep(2)}
                disabled={!sumOk || !namesOk}
                size="lg"
              >
                Дальше
                <ArrowRight />
              </Button>
            </div>
          </motion.div>
        )}

        {/* ── Шаг 3 ── */}
        {step === 2 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-7"
          >
            <p className="max-w-[60ch] text-[15px] leading-relaxed text-muted">
              Размер выборки считают до старта — это единственная защита от
              соблазна остановиться в удачный момент.{" "}
              <Term id="peeking">Подглядывание</Term> с остановкой на первом
              «значимо» поднимает долю ложных открытий впятеро.
            </p>

            <div className="grid gap-5 sm:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-[14px] text-ink">
                  Текущая конверсия, %
                </span>
                <Input
                  type="number"
                  value={baseline}
                  min={0.1}
                  max={99}
                  step={0.1}
                  onChange={(e) => setBaseline(Number(e.target.value))}
                  className="num"
                />
                <span className="mt-1.5 block text-[12px] text-faint">
                  То, что есть сейчас, без изменения.
                </span>
              </label>

              <label className="block">
                <span className="mb-2 block text-[14px] text-ink">
                  <Term id="mde">MDE</Term>, процентных пунктов
                </span>
                <Input
                  type="number"
                  value={mde}
                  min={0.1}
                  step={0.1}
                  onChange={(e) => setMde(Number(e.target.value))}
                  className="num"
                />
                <span className="mt-1.5 block text-[12px] text-faint">
                  Минимум, ради которого стоит внедрять.
                </span>
              </label>
            </div>

            <div className="rounded-xl border border-line-soft bg-surface p-7">
              {plan ? (
                <>
                  <div className="eyebrow">нужно собрать</div>
                  <div className="num mt-3 text-[clamp(36px,7vw,64px)] leading-none text-treatment">
                    {plan.sample_size_per_variant.toLocaleString("ru")}
                  </div>
                  <p className="mt-3 text-[14px] text-muted">
                    наблюдений на каждый вариант — всего{" "}
                    <span className="num text-ink">
                      {plan.sample_size_total.toLocaleString("ru")}
                    </span>{" "}
                    при <Term id="power">мощности</Term> 0,8 и{" "}
                    <Term id="alpha">alpha</Term> 0,05
                  </p>
                </>
              ) : (
                <p className="text-[14px] text-muted">
                  Проверьте параметры: конверсия и конверсия плюс MDE должны
                  лежать между 0 и 100%.
                </p>
              )}
            </div>

            {error && (
              <div className="rounded-lg border border-bad/30 bg-bad/5 p-4 text-[14px] text-bad">
                {error}
              </div>
            )}

            <div className="flex gap-3">
              <Button variant="ghost" onClick={() => setStep(1)}>
                Назад
              </Button>
              <Button onClick={create} disabled={creating} size="lg">
                <Check />
                {creating ? "Создаём…" : "Создать эксперимент"}
              </Button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
