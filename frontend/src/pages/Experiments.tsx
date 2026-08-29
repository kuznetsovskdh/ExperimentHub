import * as React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Plus } from "lucide-react";
import { api } from "@/lib/api";
import type { Experiment } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Term } from "@/components/Term";

export default function Experiments() {
  const [items, setItems] = React.useState<Experiment[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    api
      .listExperiments()
      .then(setItems)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 pt-16">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="eyebrow">все эксперименты</p>
          <h1 className="display mt-5 text-[clamp(34px,5.5vw,64px)] font-extrabold">
            Эксперименты
          </h1>
        </div>
        <Button asChild>
          <Link to="/new">
            <Plus />
            Новый эксперимент
          </Link>
        </Button>
      </div>

      {error && (
        <div className="mt-10 rounded-lg border border-bad/30 bg-bad/5 p-5 text-[14px] text-bad">
          {error}
        </div>
      )}

      {!items && !error && (
        <div className="mt-12 space-y-px overflow-hidden rounded-xl border border-line-soft bg-line-soft">
          {[0, 1].map((i) => (
            <div key={i} className="h-[104px] animate-pulse bg-surface" />
          ))}
        </div>
      )}

      {items && items.length === 0 && (
        <div className="mt-12 rounded-xl border border-line-soft bg-surface p-12 text-center">
          <p className="display text-xl">Пока ни одного эксперимента</p>
          <p className="mx-auto mt-3 max-w-[46ch] text-[14px] text-muted">
            Эксперимент — это две версии и метрика, по которой вы их
            сравниваете. Мастер проведёт по шагам и посчитает нужный размер
            выборки.
          </p>
          <Button asChild className="mt-7">
            <Link to="/new">
              Создать первый
              <ArrowRight />
            </Link>
          </Button>
        </div>
      )}

      {items && items.length > 0 && (
        <div className="mt-12 grid gap-px overflow-hidden rounded-xl border border-line-soft bg-line-soft">
          {items.map((exp, i) => (
            <motion.div
              key={exp.id}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.5 }}
            >
              <Link
                to={`/experiments/${exp.id}`}
                className="group flex flex-wrap items-center justify-between gap-5 bg-surface p-6 transition-colors hover:bg-raised"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="num text-[12px] text-faint">
                      #{exp.id}
                    </span>
                    <h2 className="display truncate text-[19px] font-semibold">
                      {exp.name}
                    </h2>
                    <Badge variant={exp.status === "active" ? "good" : "default"}>
                      {exp.status === "active" ? "активен" : "остановлен"}
                    </Badge>
                  </div>
                  <p className="mt-2 text-[13px] text-muted">
                    единица: <Term id="entity-id">{exp.entity_type}</Term>
                    {exp.variants && exp.variants.length > 0 && (
                      <>
                        {" · "}
                        {exp.variants.map((v, k) => (
                          <span key={v.id}>
                            {k > 0 && " / "}
                            <span
                              className={
                                k === 0 ? "text-control" : "text-treatment"
                              }
                            >
                              {v.name} {v.allocation_pct}%
                            </span>
                          </span>
                        ))}
                      </>
                    )}
                  </p>
                </div>

                <ArrowRight className="size-4 shrink-0 text-faint transition-all group-hover:translate-x-1 group-hover:text-treatment" />
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
