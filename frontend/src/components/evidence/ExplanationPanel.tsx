import type { ChangeEvent } from "@/types/change";
import type { EvidenceRecord } from "@/types/evidence";
import { formatArea, formatNumber } from "@/utils/formatters";

export function ExplanationPanel({
  change,
  records,
}: {
  change: ChangeEvent;
  records: EvidenceRecord[];
}) {
  const best = records.reduce<EvidenceRecord | null>(
    (top, record) =>
      record.evidence_score !== null &&
      (top === null || (top.evidence_score ?? 0) < record.evidence_score)
        ? record
        : top,
    null,
  );

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-surface-border bg-surface/50 p-3">
      <p className="text-xs font-semibold text-slate-100">Lectura del análisis</p>
      <p className="text-xs leading-relaxed text-slate-300">
        Se detectó un área de {formatArea(change.area_km2)} con tipo <code>{change.change_type}</code>{" "}
        e intensidad relativa {formatNumber(change.change_score, 3)}.{" "}
        {best
          ? `El evento contextual más cercano es ${best.event?.event_type ?? "un evento"} de ${best.event?.source ?? "una fuente externa"} con score heurístico ${formatNumber(best.evidence_score, 3)}.`
          : "No se encontró evidencia contextual cercana en el espacio y el tiempo."}
      </p>
      <p className="text-xs leading-relaxed text-amber-300/90">
        Coincidencia espacial y temporal no equivale a causalidad. Los scores no están calibrados
        como probabilidades y el tipo de cambio permanece sin clasificar.
      </p>
    </div>
  );
}
