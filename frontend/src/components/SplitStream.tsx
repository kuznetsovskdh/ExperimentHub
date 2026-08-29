import * as React from "react";

/**
 * Поток сущностей, расщепляющийся на два варианта.
 *
 * Показывает буквально то, что платформа делает с каждым entity_id: точка
 * падает на шов, хэш решает сторону, точка уходит влево или вправо и оседает
 * в своей колонке. Это не абстрактная атмосфера — это работающая модель
 * рандомизации, и доли действительно сходятся к заданному сплиту.
 *
 * Canvas, а не SVG: частиц сотни, и перерисовывать DOM было бы расточительно.
 */
type Dot = {
  x: number;
  y: number;
  vy: number;
  side: -1 | 0 | 1; // 0 — ещё не расщеплена
  vx: number;
  settled: boolean;
  r: number;
};

export function SplitStream({
  className,
  allocation = 50,
}: {
  className?: string;
  allocation?: number;
}) {
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const rafRef = React.useRef(0);
  const countsRef = React.useRef({ control: 0, treatment: 0 });
  const [counts, setCounts] = React.useState({ control: 0, treatment: 0 });

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let w = 0;
    let h = 0;
    let dots: Dot[] = [];
    const piles: number[] = [];

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const spawn = (): Dot => ({
      x: w / 2 + (Math.random() - 0.5) * 26,
      y: -10,
      vy: 0.9 + Math.random() * 1.1,
      vx: 0,
      side: 0,
      settled: false,
      r: 1.4 + Math.random() * 1.5,
    });

    const splitY = h * 0.42;
    let frame = 0;

    const step = () => {
      ctx.clearRect(0, 0, w, h);

      if (frame % 4 === 0 && dots.length < 420) dots.push(spawn());
      frame++;

      // Шов расщепления
      ctx.strokeStyle = "rgba(38,49,61,.85)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(w / 2, 0);
      ctx.lineTo(w / 2, splitY);
      ctx.stroke();

      for (const d of dots) {
        if (!d.settled) {
          d.y += d.vy;
          d.x += d.vx;

          // Момент расщепления: хэш решает сторону ровно один раз.
          if (d.side === 0 && d.y >= splitY) {
            d.side = Math.random() * 100 < allocation ? -1 : 1;
            d.vx = d.side * (0.7 + Math.random() * 0.9);
            if (d.side === -1) countsRef.current.control++;
            else countsRef.current.treatment++;
          }

          const floor = h - 14 - (piles[d.side === -1 ? 0 : 1] ?? 0) * 0.012;
          if (d.side !== 0 && d.y >= floor) {
            d.y = floor;
            d.settled = true;
            piles[d.side === -1 ? 0 : 1] =
              (piles[d.side === -1 ? 0 : 1] ?? 0) + 1;
          }
        }

        ctx.beginPath();
        ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx.fillStyle =
          d.side === 0
            ? "rgba(129,149,161,.55)"
            : d.side === -1
              ? "rgba(110,140,160,.95)"
              : "rgba(255,107,61,.95)";
        ctx.fill();
      }

      // Дошедшие до низа выбывают, чтобы поток не копился бесконечно.
      if (dots.length > 380) dots = dots.filter((d) => !d.settled || Math.random() > 0.02);

      if (frame % 20 === 0) setCounts({ ...countsRef.current });

      rafRef.current = requestAnimationFrame(step);
    };

    if (reduced) {
      // Без движения показываем итоговое состояние: смысл картинки сохраняется.
      for (let i = 0; i < 260; i++) {
        const side = Math.random() * 100 < allocation ? -1 : 1;
        dots.push({
          x: w / 2 + side * (30 + Math.random() * (w * 0.34)),
          y: h * 0.5 + Math.random() * h * 0.42,
          vy: 0,
          vx: 0,
          side,
          settled: true,
          r: 1.4 + Math.random() * 1.5,
        });
        if (side === -1) countsRef.current.control++;
        else countsRef.current.treatment++;
      }
      setCounts({ ...countsRef.current });
      ctx.clearRect(0, 0, w, h);
      for (const d of dots) {
        ctx.beginPath();
        ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx.fillStyle =
          d.side === -1 ? "rgba(110,140,160,.95)" : "rgba(255,107,61,.95)";
        ctx.fill();
      }
    } else {
      rafRef.current = requestAnimationFrame(step);
    }

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", resize);
    };
  }, [allocation]);

  const total = counts.control + counts.treatment;
  const share = (v: number) => (total ? ((v / total) * 100).toFixed(1) : "0.0");

  return (
    <div className={className}>
      <canvas ref={canvasRef} className="h-full w-full" aria-hidden="true" />
      <div className="pointer-events-none absolute inset-x-0 bottom-3 flex justify-between px-4 sm:px-8">
        <div className="text-left">
          <div className="eyebrow !text-control">control</div>
          <div className="num text-lg text-control">{share(counts.control)}%</div>
        </div>
        <div className="text-right">
          <div className="eyebrow !text-treatment">treatment</div>
          <div className="num text-lg text-treatment">
            {share(counts.treatment)}%
          </div>
        </div>
      </div>
    </div>
  );
}
