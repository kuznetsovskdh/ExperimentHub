import * as React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Check, TriangleAlert } from "lucide-react";
import { Term } from "@/components/Term";
import { Seam } from "@/components/Layout";
import { IntervalBar } from "@/components/IntervalBar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { usePlainMode } from "@/components/PlainMode";

/** Блок кода клиентского вызова — то, что реально стоит в РусТесте. */
function Code({ children, caption }: { children: string; caption?: string }) {
  return (
    <figure className="mt-5 overflow-hidden rounded-lg border border-line-soft bg-[#06090d]">
      {caption && (
        <figcaption className="border-b border-line-soft px-4 py-2 font-mono text-[11px] text-faint">
          {caption}
        </figcaption>
      )}
      <pre className="overflow-x-auto px-4 py-4">
        <code className="font-mono text-[12.5px] leading-relaxed text-ink">
          {children}
        </code>
      </pre>
    </figure>
  );
}

function Step({
  n,
  title,
  lead,
  children,
}: {
  n: string;
  title: string;
  lead: string;
  children: React.ReactNode;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
      className="relative border-t border-line-soft py-14"
    >
      {/* min-w-0 обязателен: у grid-элемента min-width по умолчанию auto,
          и длинные строки кода распирали бы страницу, несмотря на
          overflow-x-auto внутри блока. */}
      <div className="grid gap-8 md:grid-cols-[110px_1fr]">
        <div className="min-w-0">
          <div className="num sticky top-28 text-[13px] text-treatment">{n}</div>
        </div>
        <div className="min-w-0">
          <h2 className="display text-[clamp(24px,3.2vw,36px)] font-bold">
            {title}
          </h2>
          <p className="mt-4 max-w-[62ch] text-[16px] leading-relaxed text-muted">
            {lead}
          </p>
          <div className="mt-6 max-w-[68ch]">{children}</div>
        </div>
      </div>
    </motion.section>
  );
}

export default function Guide() {
  const { plain } = usePlainMode();

  return (
    <div className="relative mx-auto max-w-[1240px] px-5 pb-24">
      <Seam className="opacity-20" />

      {/* Шапка */}
      <header className="relative pb-6 pt-20">
        <p className="eyebrow">разбор на живом примере</p>
        <h1 className="display mt-6 max-w-[16ch] text-[clamp(38px,7vw,86px)] font-extrabold">
          Как сделать A/B-тест
        </h1>
        <p className="mt-7 max-w-[60ch] text-[17px] leading-relaxed text-muted">
          Ниже — настоящий эксперимент, который прогнали на пользователях
          РусТеста: помогает ли подсказка перед началом теста довести его до
          конца. Шесть шагов, реальные числа и то, чего этим числам не хватает.
        </p>
        <div className="mt-7 flex flex-wrap gap-2">
          <Badge variant="control">control — без подсказки</Badge>
          <Badge variant="treatment">treatment — с подсказкой</Badge>
          <Badge>единица: пользователь</Badge>
          <Badge>метрика: завершение теста</Badge>
        </div>
      </header>

      <Step
        n="01"
        title="Сформулировать гипотезу"
        lead="Гипотеза — это утверждение, которое можно опровергнуть. «Улучшить интерфейс» опровергнуть нельзя, а «подсказка повысит долю завершённых тестов» — можно."
      >
        <div className="rounded-lg border border-line-soft bg-surface p-6">
          <p className="text-[15px] leading-relaxed">
            <span className="text-faint">Если</span> показать пользователю
            подсказку о структуре теста перед первым вопросом,{" "}
            <span className="text-faint">то</span> доля доведённых до конца
            попыток вырастет,{" "}
            <span className="text-faint">потому что</span> люди бросают тест, не
            понимая, сколько он займёт.
          </p>
        </div>
        <p className="mt-5 text-[14px] leading-relaxed text-muted">
          Здесь же решается, что именно считать успехом. Мы выбрали завершение
          попытки: это <Term id="significant">бинарная метрика</Term> — либо да,
          либо нет.
        </p>
      </Step>

      <Step
        n="02"
        title="Выбрать единицу и поделить трафик"
        lead="Нужно решить, кого делить на группы, и в какой пропорции. Единица деления должна совпадать с тем, на кого действует изменение."
      >
        <p className="text-[15px] leading-relaxed text-muted">
          Подсказку видит конкретный человек, значит единица —{" "}
          <Term id="entity-id">пользователь</Term>. Делим поровну:{" "}
          <Term id="allocation">по 50%</Term> в каждый{" "}
          <Term id="variant">вариант</Term>.
        </p>

        <Code caption="POST /experiments/">{`{
  "name": "rustest-hint-experiment",
  "entity_type": "user",
  "variants": [
    { "name": "control",   "allocation_pct": 50 },
    { "name": "treatment", "allocation_pct": 50 }
  ]
}`}</Code>

        <p className="mt-5 text-[14px] leading-relaxed text-muted">
          Дальше продукт спрашивает у платформы вариант для каждого
          пользователя. Ответ{" "}
          <Term id="randomization">детерминирован</Term>: один и тот же человек
          всегда попадёт в тот же вариант, и интерфейс не будет прыгать между
          визитами.
        </p>

        <Code caption="result-service/app/main.py — при старте попытки">{`eh_data = eh_get_variant(user["id"])
# → {"variant_id": 4, "variant_name": "treatment"}`}</Code>
      </Step>

      <Step
        n="03"
        title="Посчитать размер выборки заранее"
        lead="Это единственная защита от соблазна остановиться в удачный момент. Число участников определяется до старта и больше не обсуждается."
      >
        <div className="grid gap-px overflow-hidden rounded-lg border border-line-soft bg-line-soft sm:grid-cols-3">
          {[
            { l: "текущая конверсия", v: "26,1%", h: "то, что есть сейчас" },
            { l: "MDE", v: "10 пп", h: "минимум, ради которого стоит внедрять" },
            { l: "нужно на вариант", v: "336", h: "при мощности 0,8" },
          ].map((x) => (
            <div key={x.l} className="bg-ground p-5">
              <div className="eyebrow">{x.l}</div>
              <div className="num mt-2 text-[26px] text-ink">{x.v}</div>
              <div className="mt-1 text-[12px] text-faint">{x.h}</div>
            </div>
          ))}
        </div>

        <p className="mt-5 text-[14px] leading-relaxed text-muted">
          <Term id="mde">MDE</Term> задают от бизнеса, а не от желания: какое
          изменение вы бы реально стали внедрять. Чем меньше эффект вы хотите
          поймать, тем больше нужно людей — вдвое меньший эффект требует вчетверо
          большей выборки.
        </p>

        <Button asChild variant="outline" size="sm" className="mt-6">
          <Link to="/tools">
            Посчитать для своей метрики
            <ArrowRight />
          </Link>
        </Button>
      </Step>

      <Step
        n="04"
        title="Собирать метрику — с нулями"
        lead="Самый неочевидный шаг и место, где эта интеграция сначала сломалась. Событие нужно слать не только при успехе."
      >
        <div className="rounded-lg border border-bad/30 bg-bad/5 p-6">
          <div className="flex items-start gap-3">
            <TriangleAlert className="mt-0.5 size-4 shrink-0 text-bad" />
            <div>
              <p className="font-medium text-ink">Как было сломано</p>
              <p className="mt-2 text-[14px] leading-relaxed text-muted">
                Клиент отправлял событие только когда тест завершён, всегда со
                значением 1. В платформу попадали одни успехи — и конверсия
                получалась 100% в обеих группах, независимо от варианта. Считать
                там было нечего.
              </p>
            </div>
          </div>
        </div>

        <p className="mt-6 text-[15px] leading-relaxed text-muted">
          Правильно — отправлять событие дважды за попытку: ноль при старте и
          единицу при завершении. Ноль и есть{" "}
          <Term id="fill-missing">знаменатель</Term>: те, кто попал в
          эксперимент, но до конца не дошёл.
        </p>

        <Code caption="result-service/app/main.py">{`# при старте попытки — ноль в знаменатель
eh_record_completion(user_id, attempt.id, completed=False)

# при завершении — единица
eh_record_completion(user_id, attempt_id, completed=True)`}</Code>

        <p className="mt-5 text-[14px] leading-relaxed text-muted">
          <code className="font-mono text-[12px] text-ink">event_key</code> вида{" "}
          <code className="font-mono text-[12px] text-ink">
            attempt-1234-finish
          </code>{" "}
          делает отправку безопасной при повторе: сеть моргнула, клиент повторил
          запрос — метрика не задвоится. А если человек проходит тест несколько
          раз, <Term id="aggregation">агрегация</Term> сведёт его к одному
          наблюдению.
        </p>
      </Step>

      <Step
        n="05"
        title="Прочитать результат"
        lead="Не «значимо или нет», а три числа вместе: насколько изменилось, насколько мы в этом уверены и могли ли мы вообще это заметить."
      >
        <div className="overflow-hidden rounded-lg border border-line-soft">
          <div className="grid grid-cols-2 gap-px bg-line-soft">
            <div className="bg-surface p-6">
              <div className="eyebrow !text-control">control</div>
              <div className="num mt-3 text-[40px] leading-none text-control">
                26,1%
              </div>
              <p className="mt-2 text-[12px] text-faint">
                6 завершили из 23 назначенных
              </p>
            </div>
            <div className="bg-surface p-6">
              <div className="eyebrow !text-treatment">treatment</div>
              <div className="num mt-3 text-[40px] leading-none text-treatment">
                57,1%
              </div>
              <p className="mt-2 text-[12px] text-faint">
                16 завершили из 28 назначенных
              </p>
            </div>
          </div>

          <div className="border-t border-line-soft bg-ground p-6">
            <IntervalBar
              effect={0.310559}
              lower={0.054}
              upper={0.567118}
              significant
            />
          </div>

          <div className="grid gap-px border-t border-line-soft bg-line-soft sm:grid-cols-3">
            <div className="bg-ground p-5">
              <div className="eyebrow">
                <Term id="p-value">p-value</Term>
              </div>
              <div className="num mt-2 text-[22px] text-good">0,026</div>
            </div>
            <div className="bg-ground p-5">
              <div className="eyebrow">
                <Term id="srm">перекос деления</Term>
              </div>
              <div className="mt-2 flex items-center gap-2 text-[15px] text-good">
                <Check className="size-4" /> не обнаружен
              </div>
            </div>
            <div className="bg-ground p-5">
              <div className="eyebrow">
                <Term id="power">мощность</Term>
              </div>
              <div className="num mt-2 text-[22px] text-warn">60,6%</div>
            </div>
          </div>
        </div>

        <p className="mt-6 text-[14px] leading-relaxed text-muted">
          {plain
            ? "Разница такая, что случайностью её объяснить трудно: примерно 3 шанса из 100. Деление на группы прошло честно. Но людей было мало, и поэтому вилка возможных значений очень широкая."
            : "p-value ниже alpha, SRM не обнаружен, интервал не накрывает ноль. При этом достигнутая мощность 60,6% и ширина интервала 51 пункт говорят о недостаточном размере выборки."}
        </p>
      </Step>

      <Step
        n="06"
        title="Принять решение — и назвать его цену"
        lead="Значимый результат не означает «внедряем и забыли». Важно, что именно вы узнали, а чего пока не узнали."
      >
        <div className="space-y-3">
          {[
            {
              icon: <Check className="size-4 text-good" />,
              t: "Что установлено",
              d: "Подсказка помогает: направление эффекта определено, перекоса в делении нет, случайностью такую разницу объяснить трудно.",
            },
            {
              icon: <TriangleAlert className="size-4 text-warn" />,
              t: "Что не установлено",
              d: "Величина эффекта. Вилка от +5 до +57 пунктов слишком широка, чтобы обещать бизнесу конкретную цифру. При мощности 60,6% значимый результат к тому же систематически завышает эффект.",
            },
            {
              icon: <ArrowRight className="size-4 text-treatment" />,
              t: "Что делать дальше",
              d: "Добрать выборку до 336 на вариант — тогда можно будет говорить не только о том, что подсказка работает, но и насколько.",
            },
          ].map((r) => (
            <div
              key={r.t}
              className="flex gap-4 rounded-lg border border-line-soft bg-surface p-5"
            >
              <div className="mt-0.5 shrink-0">{r.icon}</div>
              <div>
                <p className="font-medium text-ink">{r.t}</p>
                <p className="mt-1.5 text-[14px] leading-relaxed text-muted">
                  {r.d}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 rounded-lg border border-warn/30 bg-warn/5 p-6">
          <p className="font-medium text-warn">И одно правило напоследок</p>
          <p className="mt-2 text-[14px] leading-relaxed text-muted">
            Не смотрите на результат каждый день, останавливаясь на первом
            «значимо». <Term id="peeking">Подглядывание</Term> поднимает долю
            ложных открытий с 5% до 26,8% — это измерено на симуляциях в этой же
            платформе. Размер выборки считают заранее и досиживают до конца.
          </p>
        </div>
      </Step>

      <div className="mt-16 flex flex-wrap gap-3 border-t border-line-soft pt-10">
        <Button asChild size="lg">
          <Link to="/new">
            Создать свой эксперимент
            <ArrowRight />
          </Link>
        </Button>
        <Button asChild variant="outline" size="lg">
          <Link to="/glossary">Словарь терминов</Link>
        </Button>
      </div>
    </div>
  );
}
