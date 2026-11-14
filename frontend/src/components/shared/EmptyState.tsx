import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-2 rounded-lg border border-dashed border-surface-border p-4">
      <p className="text-sm font-medium text-slate-200">{title}</p>
      {description ? <p className="text-xs leading-relaxed text-muted">{description}</p> : null}
      {action}
    </div>
  );
}
