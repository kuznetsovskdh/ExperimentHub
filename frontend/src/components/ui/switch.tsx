import * as React from "react";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import { cn } from "@/lib/utils";

export const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitive.Root
    ref={ref}
    className={cn(
      "peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full",
      "border border-line transition-colors",
      "data-[state=checked]:bg-treatment data-[state=unchecked]:bg-raised",
      className
    )}
    {...props}
  >
    <SwitchPrimitive.Thumb
      className={cn(
        "pointer-events-none block h-3.5 w-3.5 rounded-full bg-ink shadow-lg transition-transform",
        "data-[state=checked]:translate-x-[18px] data-[state=checked]:bg-[#0a0a0a]",
        "data-[state=unchecked]:translate-x-0.5"
      )}
    />
  </SwitchPrimitive.Root>
));
Switch.displayName = "Switch";
