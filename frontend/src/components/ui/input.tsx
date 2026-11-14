import type { ComponentProps } from "react";

import { cn } from "@/utils/formatters";

export function Input({ className, ...props }: ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-md border border-surface-border bg-surface px-3 text-sm text-slate-100 placeholder:text-muted/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
