import type { ComponentProps } from "react";

import { cn } from "@/utils/formatters";

export function Select({ className, children, ...props }: ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-9 w-full rounded-md border border-surface-border bg-surface px-2 text-sm text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}
