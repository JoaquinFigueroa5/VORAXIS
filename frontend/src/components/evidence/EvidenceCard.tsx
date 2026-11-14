import { Badge } from "@/components/ui/badge";
import type { EvidenceRecord } from "@/types/evidence";
import { formatNumber } from "@/utils/formatters";

export function EvidenceCard({ record }: { record: EvidenceRecord }) {
  return (
    <li className="flex flex-col gap-1 rounded-md border border-surface-border bg-surface/60 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-slate-100">
          {record.event?.source ?? "Fuente"} · {record.event?.event_type ?? "evento"}
        </span>
        <Badge tone="info">{record.spatial_relation}</Badge>
      </div>
      <p className="text-xs text-muted">
        {record.distance_km !== null ? `${formatNumber(record.distance_km, 1)} km` : "distancia —"} ·{" "}
        {record.time_difference_hours !== null
          ? `${formatNumber(record.time_difference_hours, 1)} h`
          : "tiempo —"}{" "}
        · score {formatNumber(record.evidence_score, 3)}
      </p>
      {record.explanation ? (
        <p className="text-xs leading-relaxed text-slate-300">{record.explanation}</p>
      ) : null}
    </li>
  );
}
