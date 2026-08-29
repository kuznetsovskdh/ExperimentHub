import * as React from "react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";

/**
 * Навигация с бегущей подложкой и mix-blend-difference — по присланному
 * референсу, но подложка здесь ещё и отмечает активный маршрут, а не только
 * следует за курсором: иначе при уходе мыши пропадает признак текущей страницы.
 */
const LINKS = [
  { to: "/", label: "Начало" },
  { to: "/guide", label: "Как сделать A/B" },
  { to: "/experiments", label: "Эксперименты" },
  { to: "/tools", label: "Расчёты" },
  { to: "/glossary", label: "Словарь" },
];

type Pos = { left: number; width: number; opacity: number };

export function NavHeader() {
  const { pathname } = useLocation();
  const listRef = React.useRef<HTMLUListElement>(null);
  const itemRefs = React.useRef<(HTMLLIElement | null)[]>([]);
  const [hover, setHover] = React.useState<Pos | null>(null);

  const activeIndex = React.useMemo(() => {
    const exact = LINKS.findIndex((l) => l.to === pathname);
    if (exact !== -1) return exact;
    const prefix = LINKS.findIndex(
      (l) => l.to !== "/" && pathname.startsWith(l.to)
    );
    return prefix;
  }, [pathname]);

  const [activePos, setActivePos] = React.useState<Pos | null>(null);

  const measure = React.useCallback(() => {
    const el = itemRefs.current[activeIndex];
    if (!el) {
      setActivePos(null);
      return;
    }
    setActivePos({
      left: el.offsetLeft,
      width: el.getBoundingClientRect().width,
      opacity: 1,
    });
  }, [activeIndex]);

  React.useLayoutEffect(() => {
    measure();

    // Шрифты грузятся асинхронно, и до их применения ширины пунктов другие.
    // Без повторного замера подложка навсегда остаётся на координатах,
    // посчитанных по запасному шрифту, и не совпадает с активным пунктом.
    if (document.fonts?.status !== "loaded") {
      document.fonts?.ready.then(measure).catch(() => undefined);
    }

    // Пересчёт при изменении размеров: ширина пунктов зависит от брейкпоинта.
    const list = listRef.current;
    if (!list || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(measure);
    ro.observe(list);
    return () => ro.disconnect();
  }, [measure, pathname]);

  const pos = hover ?? activePos ?? { left: 0, width: 0, opacity: 0 };

  return (
    <ul
      ref={listRef}
      onMouseLeave={() => setHover(null)}
      className="relative flex w-fit items-center rounded-full border border-line bg-surface/80 p-1 backdrop-blur"
    >
      {LINKS.map((link, i) => (
        <li
          key={link.to}
          ref={(el) => {
            itemRefs.current[i] = el;
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget;
            setHover({
              left: el.offsetLeft,
              width: el.getBoundingClientRect().width,
              opacity: 1,
            });
          }}
          className="relative z-10 mix-blend-difference"
        >
          <Link
            to={link.to}
            className="block whitespace-nowrap px-3 py-1.5 text-[12px] text-white sm:px-4 sm:text-[13px]"
          >
            {link.label}
          </Link>
        </li>
      ))}

      <motion.li
        aria-hidden="true"
        animate={pos}
        transition={{ type: "spring", stiffness: 380, damping: 32 }}
        className="absolute z-0 h-[30px] rounded-full bg-ink sm:h-[32px]"
      />
    </ul>
  );
}
