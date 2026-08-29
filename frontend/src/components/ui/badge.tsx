import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import * as React from "react";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-mono uppercase tracking-wider",
  {
    variants: {
      variant: {
        default: "border-line text-muted",
        control: "border-control/40 text-control bg-control/10",
        treatment: "border-treatment/40 text-treatment bg-treatment/10",
        good: "border-good/40 text-good bg-good/10",
        warn: "border-warn/40 text-warn bg-warn/10",
        bad: "border-bad/40 text-bad bg-bad/10",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export function Badge({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
