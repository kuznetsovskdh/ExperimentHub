import * as React from "react";
import { motion } from "framer-motion";
import { TriangleAlert } from "lucide-react";
import { glossary } from "@/lib/glossary";
import { Input } from "@/components/ui/input";
import { usePlainMode, PlainModeToggle } from "@/components/PlainMode";

export default function GlossaryPage() {
  const { plain } = usePlainMode();
  const [q, setQ] = React.useState("");

  const entries = React.useMemo(() => {
    const list = Object.entries(glossary);
    const needle = q.trim().toLowerCase();
    if (!needle) return list;
    return list.filter(
      ([id, e]) =>
        id.includes(needle) ||
        e.title.toLowerCase().includes(needle) ||
        e.plain.toLowerCase().includes(needle) ||
        e.precise.toLowerCase().includes(needle)
    );
  }, [q]);

  return (
    <div className="mx-auto max-w-[900px] px-5 pb-24 pt-16">
      <p className="eyebrow">словарь</p>
      <h1 className="display mt-5 text-[clamp(32px,5vw,58px)] font-extrabold">
        Что значат эти слова
      </h1>
      <p className="mt-6 max-w-[58ch] text-[16px] leading-relaxed text-muted">
        Каждый термин объяснён дважды: простыми словами и точно. Переключатель
        меняет регистр здесь и во всех подсказках интерфейса.
      </p>

      <div className="mt-8 flex flex-wrap items-center gap-5">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="найти термин…"
          className="max-w-xs"
        />
        <PlainModeToggle />
      </div>

      <div className="mt-12 space-y-px overflow-hidden rounded-xl border border-line-soft bg-line-soft">
        {entries.map(([id, e], i) => (
          <motion.article
            key={id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.03, 0.3), duration: 0.4 }}
            className="bg-surface p-7"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h2 className="display text-[20px] font-semibold">{e.title}</h2>
              <code className="font-mono text-[11px] text-faint">{id}</code>
            </div>

            <p className="mt-4 max-w-[68ch] text-[15px] leading-relaxed text-muted">
              {plain ? e.plain : e.precise}
            </p>

            {/* Второй регистр остаётся доступен — просто ниже и тише. */}
            <details className="group mt-4">
              <summary className="cursor-pointer list-none text-[12.5px] text-faint transition-colors hover:text-muted">
                {plain ? "показать точную формулировку" : "объяснить проще"}
              </summary>
              <p className="mt-3 max-w-[68ch] border-l-2 border-line pl-4 text-[14px] leading-relaxed text-muted">
                {plain ? e.precise : e.plain}
              </p>
            </details>

            {e.pitfall && (
              <div className="mt-5 flex gap-3 rounded-lg border border-warn/25 bg-warn/[0.04] p-4">
                <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warn" />
                <p className="max-w-[62ch] text-[13.5px] leading-relaxed text-muted">
                  {e.pitfall}
                </p>
              </div>
            )}
          </motion.article>
        ))}

        {entries.length === 0 && (
          <div className="bg-surface p-12 text-center text-muted">
            Ничего не нашлось по запросу «{q}».
          </div>
        )}
      </div>
    </div>
  );
}
