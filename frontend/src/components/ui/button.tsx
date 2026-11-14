import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "@/utils/formatters";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-accent text-surface hover:bg-accent/90",
        secondary:
          "border border-surface-border bg-surface-raised text-slate-100 hover:bg-surface-border/60",
        ghost: "text-slate-200 hover:bg-surface-border/60",
        danger: "bg-red-600 text-white hover:bg-red-500",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export type ButtonProps = ComponentProps<"button"> & VariantProps<typeof buttonVariants>;

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
