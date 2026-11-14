import { LoaderCircle } from "lucide-react";

export function LoadingState({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 p-4 text-sm text-muted">
      <LoaderCircle className="h-4 w-4 animate-spin text-accent" aria-hidden />
      <span>{label}</span>
    </div>
  );
}
