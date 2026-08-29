import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-all disabled:pointer-events-none disabled:opacity-40 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        // Основное действие несёт цвет treatment — того варианта, который проверяют.
        default:
          "bg-treatment text-[#0a0a0a] hover:brightness-110 active:brightness-95",
        outline:
          "border border-line bg-transparent text-ink hover:border-treatment hover:text-white",
        ghost: "bg-transparent text-muted hover:text-ink hover:bg-raised",
        danger: "bg-bad text-white hover:brightness-110",
      },
      size: {
        sm: "h-8 px-3 text-[13px] rounded-sm",
        default: "h-10 px-5 text-sm rounded-md",
        lg: "h-12 px-7 text-[15px] rounded-md",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size }), className)}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
