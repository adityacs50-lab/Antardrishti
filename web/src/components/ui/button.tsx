import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-series-1 text-white hover:bg-series-1/85",
        secondary: "bg-surface-raised text-ink hover:bg-surface-raised/70 border border-line",
        outline: "border border-line-strong bg-transparent text-ink hover:bg-surface-raised",
        ghost: "text-ink-muted hover:bg-surface-raised hover:text-ink",
        confirm: "bg-status-good/15 text-status-good border border-status-good/40 hover:bg-status-good/25",
        override: "bg-status-warning/15 text-status-warning border border-status-warning/40 hover:bg-status-warning/25",
        danger: "bg-status-critical/15 text-status-critical border border-status-critical/40 hover:bg-status-critical/25",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-6",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
  },
);
Button.displayName = "Button";
export { buttonVariants };
