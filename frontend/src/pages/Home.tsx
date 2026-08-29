import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { SplitStream } from "@/components/SplitStream";
import { BackgroundPaths } from "@/components/BackgroundPaths";
import { Seam } from "@/components/Layout";
import { Term } from "@/components/Term";
import { Button } from "@/components/ui/button";

const rise = {
  hidden: { opacity: 0, y: 22 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.75, ease: [0.16, 1, 0.3, 1] },
  }),
};

export default function Home() {
  return (
    <div>
      {/* ── Тезис ─────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <BackgroundPaths className="absolute inset-0 opacity-70" />
        <Seam className="opacity-40" />

        <div className="relative mx-auto max-w-[1240px] px-5 pb-16 pt-20 sm:pt-28">
          <motion.p
            custom={0}
            variants={rise}
            initial="hidden"
            animate="show"
            className="eyebrow"
          >
            платформа экспериментов
          </motion.p>

          <motion.h1
            custom={1}
            variants={rise}
            initial="hidden"
            animate="show"
            className="display mt-6 text-[clamp(44px,9vw,116px)] font-extrabold"
          >
            Одна аудитория.
            <br />
            <span className="text-control">Две</span> реальности.
            <br />
            <span className="text-treatment">Одна</span> разница.
          </motion.h1>

          <motion.p
            custom={2}
            variants={rise}
            initial="hidden"
            animate="show"
            className="mt-8 max-w-[52ch] text-[17px] leading-relaxed text-muted sm:text-[19px]"
          >
            Эксперимент — это когда вы делите людей на две группы, одной
            показываете новое, а другой оставляете старое, и честно смотрите,
            что вышло. ExperimentHub делит, собирает и считает — и объясняет
            каждое число, а не просто показывает его.
          </motion.p>

          <motion.div
            custom={3}
            variants={rise}
            initial="hidden"
            animate="show"
            className="mt-10 flex flex-wrap items-center gap-3"
          >
            <Button asChild size="lg">
              <Link to="/guide">
                Разобрать на реальном примере
                <ArrowRight />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link to="/experiments">Смотреть эксперименты</Link>
            </Button>
          </motion.div>
        </div>
      </section>

      {/* ── Расщепление вживую ────────────────────────────────────────── */}
      <section className="mx-auto max-w-[1240px] px-5">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 1 }}
          className="relative h-[340px] overflow-hidden rounded-xl border border-line-soft bg-surface sm:h-[420px]"
        >
          <SplitStream className="relative h-full w-full" allocation={50} />
        </motion.div>

        <p className="mx-auto mt-5 max-w-[62ch] text-center text-[13px] leading-relaxed text-faint">
          Так работает <Term id="randomization">рандомизация</Term>. Каждая
          точка — один <Term id="entity-id">пользователь или товар</Term>. Куда
          он попадёт, решает хэш его идентификатора: один и тот же человек
          всегда окажется в одном и том же варианте, а доли сходятся к
          заданному сплиту.
        </p>
      </section>

      {/* ── Три вещи, которые платформа не даст сделать неправильно ───── */}
      <section className="mx-auto mt-28 max-w-[1240px] px-5">
        <h2 className="display max-w-[18ch] text-[clamp(30px,4.6vw,54px)] font-bold">
          Считать легко. Трудно не обмануть себя.
        </h2>
        <p className="mt-5 max-w-[58ch] text-muted">
          Ошибка в эксперименте не выглядит как ошибка. Она выглядит как
          результат. Поэтому платформа не молчит там, где вывод шаткий.
        </p>

        <div className="mt-14 grid gap-px overflow-hidden rounded-xl border border-line-soft bg-line-soft md:grid-cols-3">
          {[
            {
              n: "01",
              t: "Проверяет деление до подсчёта",
              d: (
                <>
                  Если группы поделились не так, как задумано, платформа
                  сообщает об этом раньше, чем покажет эффект.{" "}
                  <Term id="srm">Перекос распределения</Term> обесценивает любой
                  p-value.
                </>
              ),
            },
            {
              n: "02",
              t: "Называет размер неопределённости",
              d: (
                <>
                  Вместо «значимо» вы получаете{" "}
                  <Term id="confidence-interval">вилку значений</Term>, в
                  которой лежит истинный эффект, и{" "}
                  <Term id="power">мощность</Term> — шанс, что вы вообще могли
                  его заметить.
                </>
              ),
            },
            {
              n: "03",
              t: "Предупреждает о подглядывании",
              d: (
                <>
                  <Term id="peeking">Ежедневные проверки</Term> с остановкой на
                  первом «значимо» дают 26,8% ложных открытий вместо 5%. Это
                  измерено здесь же, на симуляциях.
                </>
              ),
            },
          ].map((c, i) => (
            <motion.div
              key={c.n}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ delay: i * 0.1, duration: 0.6 }}
              className="bg-ground p-7"
            >
              <div className="num text-[11px] text-treatment">{c.n}</div>
              <h3 className="display mt-4 text-[19px] font-semibold leading-snug">
                {c.t}
              </h3>
              <p className="mt-3 text-[14px] leading-relaxed text-muted">
                {c.d}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Переход в гайд ────────────────────────────────────────────── */}
      <section className="relative mx-auto mt-28 max-w-[1240px] px-5">
        <div className="relative overflow-hidden rounded-xl border border-line-soft bg-surface p-8 sm:p-14">
          <Seam className="opacity-30" />
          <div className="relative grid items-center gap-10 md:grid-cols-2">
            <div>
              <p className="eyebrow">живой пример</p>
              <h2 className="display mt-4 text-[clamp(26px,3.8vw,42px)] font-bold">
                A/B-тест, который реально прогнали
              </h2>
              <p className="mt-5 max-w-[46ch] text-[15px] leading-relaxed text-muted">
                Подсказка перед началом теста в РусТесте: помогает ли она
                довести тест до конца. Весь путь — от гипотезы до решения, с
                настоящими цифрами и честным разбором того, чего этим цифрам
                не хватает.
              </p>
              <Button asChild className="mt-8">
                <Link to="/guide">
                  Пройти по шагам
                  <ArrowRight />
                </Link>
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line-soft bg-line-soft">
              <div className="bg-ground p-6">
                <div className="eyebrow !text-control">control</div>
                <div className="num mt-3 text-[38px] leading-none text-control">
                  26,1%
                </div>
                <p className="mt-2 text-[12px] text-faint">6 из 23 завершили</p>
              </div>
              <div className="bg-ground p-6">
                <div className="eyebrow !text-treatment">treatment</div>
                <div className="num mt-3 text-[38px] leading-none text-treatment">
                  57,1%
                </div>
                <p className="mt-2 text-[12px] text-faint">16 из 28 завершили</p>
              </div>
              <div className="col-span-2 bg-ground p-6">
                <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
                  <span className="num text-[22px] text-ink">+31,1 пп</span>
                  <span className="text-[13px] text-muted">
                    <Term id="p-value">p</Term> = 0,026
                  </span>
                  <span className="text-[13px] text-warn">
                    <Term id="power">мощность</Term> 60,6%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
