import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "@/utils/formatters";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      tone: {
        neutral: "border-surface-border bg-surface-raised text-slate-200",
        info: "border-sky-500/40 bg-sky-500/10 text-sky-300",
        success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
        warning: "border-amber-500/40 bg-amber-500/10 text-amber-300",
        danger: "border-red-500/40 bg-red-500/10 text-red-300",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export type BadgeProps = ComponentProps<"span"> & VariantProps<typeof badgeVariants>;

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
