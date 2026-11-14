import { API_URL } from "@/services/api";

export function Header() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-surface-border px-4">
      <p className="text-sm font-medium text-slate-200">
        Observación de cambios · Radar de apertura sintética
      </p>
      <div className="flex items-center gap-4 text-xs text-muted">
        <span className="hidden sm:inline">API: {API_URL}</span>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="rounded-md border border-surface-border px-2 py-1 text-slate-200 hover:bg-surface-border/60"
        >
          Documentación API
        </a>
      </div>
    </header>
  );
}
