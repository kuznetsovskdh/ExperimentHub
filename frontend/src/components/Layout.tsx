import * as React from "react";
import { Link } from "react-router-dom";
import { NavHeader } from "@/components/NavHeader";
import { PlainModeToggle } from "@/components/PlainMode";
import { isDemoMode, onDemoModeChange } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Бейдж демо-режима.
 *
 * Показывается, как только чтение ушло на запасные данные. Подмена данных
 * не должна происходить незаметно: человек имеет право знать, что смотрит
 * на сохранённый слепок, а не на живой эксперимент.
 */
function DemoBadge() {
  const [demo, setDemo] = React.useState(isDemoMode());
  React.useEffect(() => onDemoModeChange(setDemo) as unknown as () => void, []);

  if (!demo) return null;
  return (
    <div className="flex items-center gap-2 rounded-full border border-warn/40 bg-warn/10 px-3 py-1">
      <span className="size-1.5 rounded-full bg-warn" />
      <span className="font-mono text-[10px] uppercase tracking-wider text-warn">
        демо-данные
      </span>
    </div>
  );
}

/** Вертикальный шов — линия расщепления, проходящая через все страницы. */
export function Seam({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "seam pointer-events-none absolute inset-y-0 left-1/2 w-px -translate-x-1/2",
        className
      )}
    />
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen">
      <header className="sticky top-0 z-40 border-b border-line-soft bg-ground/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1240px] flex-wrap items-center justify-between gap-4 px-5 py-3">
          <Link to="/" className="group flex shrink-0 items-center gap-2.5">
            {/* Знак: две доли, расходящиеся от шва. */}
            <span className="flex items-center gap-[3px]" aria-hidden="true">
              <span className="h-4 w-[3px] bg-control transition-all group-hover:h-5" />
              <span className="h-5 w-px bg-line" />
              <span className="h-4 w-[3px] bg-treatment transition-all group-hover:h-5" />
            </span>
            <span className="display text-[15px] font-semibold tracking-tight">
              ExperimentHub
            </span>
          </Link>

          {/* До lg навигация переезжает во вторую строку: на 768px она
              вместе с логотипом и переключателем не помещается в ряд. */}
          <div className="hidden lg:block">
            <NavHeader />
          </div>

          <div className="flex items-center gap-4">
            <DemoBadge />
            <PlainModeToggle className="hidden sm:block" />
          </div>
        </div>

        <div className="border-t border-line-soft px-5 py-2 lg:hidden">
          <div className="overflow-x-auto">
            <NavHeader />
          </div>
        </div>
      </header>

      <main>{children}</main>

      <footer className="mt-24 border-t border-line-soft">
        <div className="mx-auto flex max-w-[1240px] flex-col gap-3 px-5 py-8 text-[12px] text-faint sm:flex-row sm:items-center sm:justify-between">
          <p>
            ExperimentHub — платформа экспериментов, не зависящая от домена
            продукта.
          </p>
          <p className="font-mono">
            <a
              href="/api/docs"
              className="transition-colors hover:text-treatment"
            >
              документация API →
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}
