import type { ProcessingJob } from "@/types/job";
import { formatDateTime } from "@/utils/formatters";

export function ChangeTimeline({
  beforeDate,
  afterDate,
  job,
}: {
  beforeDate?: string | null;
  afterDate?: string | null;
  job?: ProcessingJob;
}) {
  const entries = [
    { label: "Adquisición before", value: beforeDate, tone: "bg-sky-400" },
    { label: "Adquisición after", value: afterDate, tone: "bg-sky-300" },
    { label: "Trabajo creado", value: job?.created_at, tone: "bg-orange-400" },
    { label: "Trabajo finalizado", value: job?.finished_at, tone: "bg-emerald-400" },
  ].filter((entry) => Boolean(entry.value));

  return (
    <ol className="flex flex-col gap-0">
      {entries.map((entry, index) => (
        <li key={entry.label} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span className={`mt-1 h-2 w-2 rounded-full ${entry.tone}`} aria-hidden />
            {index < entries.length - 1 ? (
              <span className="h-full w-px bg-surface-border" aria-hidden />
            ) : null}
          </div>
          <div className="pb-3">
            <p className="text-xs font-medium text-slate-200">{entry.label}</p>
            <p className="text-xs text-muted">{formatDateTime(entry.value)}</p>
          </div>
        </li>
      ))}
      {entries.length === 0 ? <li className="text-xs text-muted">Sin fechas disponibles.</li> : null}
    </ol>
  );
}
