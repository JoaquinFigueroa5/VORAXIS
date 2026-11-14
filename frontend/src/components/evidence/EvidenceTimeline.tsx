import type { EvidenceRecord } from "@/types/evidence";
import { formatDateTime } from "@/utils/formatters";

export function EvidenceTimeline({ records }: { records: EvidenceRecord[] }) {
  if (records.length === 0) {
    return <p className="text-xs text-muted">Sin eventos para ubicar en el tiempo.</p>;
  }

  return (
    <ol className="flex flex-col gap-2">
      {records.map((record) => (
        <li
          key={record.id}
          className="flex items-baseline justify-between gap-2 border-l-2 border-accent/60 pl-3 text-xs"
        >
          <span className="text-slate-200">
            {record.event?.event_type ?? "evento"} · {record.event?.source ?? "—"}
          </span>
          <span className="text-muted">{formatDateTime(record.event?.event_date)}</span>
        </li>
      ))}
    </ol>
  );
}
