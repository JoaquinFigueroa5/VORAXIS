import { TriangleAlert } from "lucide-react";

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Error inesperado";
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-red-500/40 bg-red-500/5 p-4">
      <div className="flex items-center gap-2 text-sm font-medium text-red-300">
        <TriangleAlert className="h-4 w-4" aria-hidden />
        <span>No se pudo completar la operación</span>
      </div>
      <p className="text-xs leading-relaxed text-red-200/80">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="self-start text-xs font-medium text-red-200 underline underline-offset-2"
        >
          Reintentar
        </button>
      ) : null}
    </div>
  );
}
