import * as React from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { glossary } from "@/lib/glossary";
import { usePlainMode } from "@/components/PlainMode";
import { cn } from "@/lib/utils";

/**
 * Инлайн-подсказка к статистическому термину.
 *
 * На указывающих устройствах — тултип по наведению, на сенсорных — поповер
 * по нажатию: hover там не существует, и подсказка была бы недоступна.
 * Триггер всегда кнопка, поэтому термин доступен с клавиатуры.
 */
function useIsTouch() {
  const [touch, setTouch] = React.useState(false);
  React.useEffect(() => {
    setTouch(window.matchMedia("(hover: none)").matches);
  }, []);
  return touch;
}

function TermBody({ id }: { id: string }) {
  const { plain } = usePlainMode();
  const entry = glossary[id];
  if (!entry) return null;

  return (
    <div className="space-y-2.5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-display text-[13px] font-semibold text-ink">
          {entry.title}
        </span>
        <span className="eyebrow shrink-0 !text-[9px]">
          {plain ? "простыми словами" : "точно"}
        </span>
      </div>

      <p className="text-muted">{plain ? entry.plain : entry.precise}</p>

      {entry.pitfall && (
        <p className="border-l-2 border-warn/60 pl-3 text-[12px] text-warn/90">
          {entry.pitfall}
        </p>
      )}
    </div>
  );
}

export function Term({
  id,
  children,
  className,
}: {
  id: string;
  children?: React.ReactNode;
  className?: string;
}) {
  const isTouch = useIsTouch();
  const entry = glossary[id];
  const label = children ?? entry?.title ?? id;

  if (!entry) return <>{label}</>;

  const trigger = (
    <button
      type="button"
      className={cn("term-underline bg-transparent p-0 text-left", className)}
      aria-label={`${entry.title} — показать объяснение`}
    >
      {label}
    </button>
  );

  if (isTouch) {
    return (
      <Popover>
        <PopoverTrigger asChild>{trigger}</PopoverTrigger>
        <PopoverContent>
          <TermBody id={id} />
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{trigger}</TooltipTrigger>
      <TooltipContent>
        <TermBody id={id} />
      </TooltipContent>
    </Tooltip>
  );
}
