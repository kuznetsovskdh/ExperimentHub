import { motion } from "framer-motion";

/**
 * Фоновые траектории — по присланному референсу, но перекрашенные в два
 * полюса эксперимента: половина линий уходит в control, половина в treatment.
 * Даже фон здесь повторяет тему расщепления, а не просто украшает.
 */
function Paths({ position, tint }: { position: number; tint: string }) {
  const paths = Array.from({ length: 28 }, (_, i) => ({
    id: i,
    d: `M-${380 - i * 5 * position} -${189 + i * 6}C-${
      380 - i * 5 * position
    } -${189 + i * 6} -${312 - i * 5 * position} ${216 - i * 6} ${
      152 - i * 5 * position
    } ${343 - i * 6}C${616 - i * 5 * position} ${470 - i * 6} ${
      684 - i * 5 * position
    } ${875 - i * 6} ${684 - i * 5 * position} ${875 - i * 6}`,
    width: 0.4 + i * 0.028,
  }));

  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 696 316"
      fill="none"
      aria-hidden="true"
      style={{ color: tint }}
    >
      {paths.map((path) => (
        <motion.path
          key={path.id}
          d={path.d}
          stroke="currentColor"
          strokeWidth={path.width}
          strokeOpacity={0.05 + path.id * 0.012}
          initial={{ pathLength: 0.3, opacity: 0.5 }}
          animate={{
            pathLength: 1,
            opacity: [0.2, 0.45, 0.2],
            pathOffset: [0, 1, 0],
          }}
          transition={{
            duration: 24 + Math.random() * 12,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      ))}
    </svg>
  );
}

export function BackgroundPaths({ className }: { className?: string }) {
  return (
    <div className={className} aria-hidden="true">
      <Paths position={1} tint="var(--control)" />
      <Paths position={-1} tint="var(--treatment)" />
    </div>
  );
}
