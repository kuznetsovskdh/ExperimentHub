import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Нативный select: на форме с пятью управляющими параметрами родной
 * выпадающий список работает предсказуемее кастомного — особенно с клавиатуры
 * и на мобильных.
 */
export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "h-10 w-full appearance-none rounded-md border border-line bg-ground px-3 text-sm text-ink",
      "transition-colors focus:border-treatment focus:outline-none",
      "bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%2212%22 fill=%22none%22 stroke=%22%238195a1%22 stroke-width=%221.6%22><path d=%22M2 4.5L6 8.5L10 4.5%22/></svg>')] bg-[right_12px_center] bg-no-repeat pr-9",
      className
    )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";
