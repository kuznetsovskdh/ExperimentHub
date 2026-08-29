import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "h-10 w-full rounded-md border border-line bg-ground px-3 text-sm text-ink",
      "placeholder:text-faint transition-colors",
      "focus:border-treatment focus:outline-none",
      "disabled:opacity-40",
      className
    )}
    {...props}
  />
));
Input.displayName = "Input";
