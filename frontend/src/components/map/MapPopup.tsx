import { X } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/utils/formatters";

export function MapPopup({
  title,
  onClose,
  children,
  className,
}: {
  title: string;
  onClose?: () => void;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "absolute left-4 top-4 z-20 w-72 rounded-lg border border-surface-border bg-surface-raised/95 p-3 shadow-xl backdrop-blur",
        className,
      )}
      role="dialog"
      aria-label={title}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
        {onClose ? (
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose} aria-label="Cerrar">
            <X className="h-3.5 w-3.5" aria-hidden />
          </Button>
        ) : null}
      </div>
      <div className="flex flex-col gap-1 text-xs text-slate-300">{children}</div>
    </div>
  );
}
