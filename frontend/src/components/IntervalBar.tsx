import { motion } from "framer-motion";
import { pp } from "@/lib/utils";

/**
 * Доверительный интервал как главный график, а не сноска под p-value.
 *
 * Читается одним взглядом: где стоит оценка, насколько она размазана и —
 * главное — пересекает ли размах вертикальный шов нуля. Пересёк, значит
 * эффект не доказан, какими бы крупными ни были проценты рядом.
 */
export function IntervalBar({
  effect,
  lower,
  upper,
  significant,
}: {
  effect: number;
  lower: number;
  upper: number;
  significant: boolean;
}) {
  // Шкала симметрична относительно нуля: иначе ноль уезжает от центра и
  // «пересекает или нет» перестаёт читаться геометрически.
  const span = Math.max(Math.abs(lower), Math.abs(upper), Math.abs(effect)) * 1.25 || 1;
  const toPct = (v: number) => ((v + span) / (2 * span)) * 100;

  const left = toPct(lower);
  const right = toPct(upper);
  const mid = toPct(effect);
  const color = significant ? "var(--treatment)" : "var(--muted)";

  return (
    <div className="w-full">
      <div className="relative h-24">
        {/* Ось */}
        <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-line-soft" />

        {/* Шов нуля — та же линия расщепления, что проходит через весь интерфейс */}
        <div className="absolute inset-y-2 left-1/2 w-px -translate-x-1/2 bg-line" />
        <div className="absolute left-1/2 top-0 -translate-x-1/2 font-mono text-[10px] text-faint">
          0
        </div>

        {/* Размах интервала */}
        <motion.div
          className="absolute top-1/2 h-9 -translate-y-1/2 rounded-[3px]"
          style={{
            background: `color-mix(in srgb, ${color} 22%, transparent)`,
            borderLeft: `2px solid ${color}`,
            borderRight: `2px solid ${color}`,
          }}
          initial={{ left: "50%", width: 0 }}
          animate={{ left: `${left}%`, width: `${right - left}%` }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        />

        {/* Точечная оценка */}
        <motion.div
          className="absolute top-1/2 h-14 w-[3px] -translate-y-1/2"
          style={{ background: color }}
          initial={{ left: "50%", opacity: 0 }}
          animate={{ left: `${mid}%`, opacity: 1 }}
          transition={{ duration: 0.9, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        />

        {/* Подписи границ */}
        <div
          className="num absolute bottom-0 -translate-x-1/2 text-[11px] text-faint"
          style={{ left: `${left}%` }}
        >
          {pp(lower)}
        </div>
        <div
          className="num absolute bottom-0 -translate-x-1/2 text-[11px] text-faint"
          style={{ left: `${right}%` }}
        >
          {pp(upper)}
        </div>
      </div>

      <p className="mt-3 text-[13px] leading-relaxed text-muted">
        {significant ? (
          <>
            Интервал не пересекает ноль — значит направление изменения
            установлено. Но истинный эффект может лежать в любой точке от{" "}
            <span className="num text-ink">{pp(lower)}</span> до{" "}
            <span className="num text-ink">{pp(upper)}</span>.
          </>
        ) : (
          <>
            Интервал пересекает ноль: данные совместимы и с ростом, и с
            падением. Эффект не доказан — это не то же самое, что «эффекта нет».
          </>
        )}
      </p>
    </div>
  );
}
