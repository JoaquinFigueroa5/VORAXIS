import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { InsightsSummary as Summary } from "@/types/analysis";
import { formatArea } from "@/utils/formatters";

export function InsightsSummary({ summary }: { summary: Summary }) {
  const tiles = [
    { label: "Regiones", value: summary.locations },
    { label: "Escenas NISAR", value: summary.scenes },
    { label: "Observaciones", value: summary.observations },
    { label: "Cambios", value: summary.change_events },
    { label: "Área cambiada", value: formatArea(summary.change_area_km2) },
    { label: "Evidencias", value: summary.evidence_records },
    { label: "Eventos auxiliares", value: summary.auxiliary_events },
    {
      label: "Trabajos",
      value: Object.values(summary.jobs).reduce((total, count) => total + count, 0),
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
      {tiles.map((tile) => (
        <Card key={tile.label}>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium text-muted">{tile.label}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-semibold text-slate-100">{tile.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
