import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams, Link } from "react-router-dom";

import { AnalysisPanel } from "@/components/analysis/AnalysisPanel";
import { AnalysisProgress } from "@/components/analysis/AnalysisProgress";
import { ChangeMetrics } from "@/components/analysis/ChangeMetrics";
import { ChangeTimeline } from "@/components/analysis/ChangeTimeline";
import { ComparisonSlider } from "@/components/analysis/ComparisonSlider";
import { EarthMap } from "@/components/map/EarthMap";
import { MapLegend } from "@/components/map/MapLegend";
import { MapPopup } from "@/components/map/MapPopup";
import { ChangeLayer } from "@/components/map/ChangeLayer";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useChanges } from "@/hooks/useChanges";
import { useJobStatus } from "@/hooks/useJobStatus";
import { jobsService } from "@/services/jobs.service";
import { useAnalysisStore } from "@/stores/analysis.store";
import { useMapStore } from "@/stores/map.store";
import { changesToFeatureCollection } from "@/utils/geometry";
import { formatArea, formatNumber, formatPercent } from "@/utils/formatters";

export function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const locationId = useMapStore((state) => state.selectedLocationId);

  if (!id || id === "new") {
    return (
      <div className="h-full overflow-y-auto p-4">
        <div className="mx-auto w-full max-w-md">
          <AnalysisPanel locationId={locationId} />
          <p className="mt-3 text-center text-xs text-muted">
            ¿Falta una región?{" "}
            <Link to="/explorer" className="text-accent underline underline-offset-2">
              Selecciona una en el explorador
            </Link>
            .
          </p>
        </div>
      </div>
    );
  }

  return <JobView jobId={id} />;
}

function JobView({ jobId }: { jobId: string }) {
  const job = useJobStatus(jobId);
  const changes = useChanges(jobId);
  const selectedChangeId = useAnalysisStore((state) => state.selectedChangeId);
  const selectChange = useAnalysisStore((state) => state.selectChange);
  const queryClient = useQueryClient();
  const [closedPopup, setClosedPopup] = useState(false);

  const cancel = useMutation({
    mutationFn: () => jobsService.cancel(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["job", jobId] }),
  });

  if (job.isLoading) return <LoadingState label="Consultando el trabajo…" />;
  if (job.isError) return <div className="p-4"><ErrorState error={job.error} /></div>;
  if (!job.data) return null;

  const selected =
    changes.data?.find((change) => change.id === selectedChangeId) ?? changes.data?.[0];

  return (
    <div className="grid h-full min-h-0 grid-cols-1 overflow-y-auto lg:grid-cols-[360px_1fr_340px] lg:overflow-hidden">
      <aside className="flex min-h-0 flex-col gap-3 overflow-y-auto border-r border-surface-border p-4">
        <AnalysisProgress job={job.data} />
        {job.data.status === "PENDING" || job.data.status === "RUNNING" ? (
          <Button
            variant="secondary"
            onClick={() => cancel.mutate()}
            disabled={cancel.isPending}
          >
            {cancel.isPending ? "Cancelando…" : "Cancelar trabajo"}
          </Button>
        ) : null}
        {cancel.isError ? <ErrorState error={cancel.error} /> : null}
        <Card>
          <CardHeader>
            <CardTitle>Línea de tiempo</CardTitle>
          </CardHeader>
          <CardContent>
            <ChangeTimeline job={job.data} />
          </CardContent>
        </Card>
        <ComparisonSlider />
      </aside>

      <div className="relative min-h-[360px]">
        <EarthMap
          fitTo={
            changes.data && changes.data.length > 0
              ? changesToFeatureCollection(changes.data)
              : undefined
          }
          initialCenter={[-90.2, 16.8]}
          initialZoom={7}
        >
          <ChangeLayer data={changesToFeatureCollection(changes.data ?? [])} />
        </EarthMap>
        <MapLegend />
        {selected && !closedPopup ? (
          <MapPopup
            title={`Cambio ${selected.id.slice(0, 8)}`}
            onClose={() => setClosedPopup(true)}
          >
            <span>Área: {formatArea(selected.area_km2)}</span>
            <span>Score relativo: {formatNumber(selected.change_score, 3)}</span>
            <span>Píxeles válidos: {formatPercent(selected.valid_pixel_percentage)}</span>
            <span>Tipo: {selected.change_type}</span>
            <Link to={`/insights/${selected.id}`} className="mt-1 text-accent underline underline-offset-2">
              Ver evidencia
            </Link>
          </MapPopup>
        ) : null}
      </div>

      <aside className="flex min-h-0 flex-col gap-3 overflow-y-auto border-l border-surface-border p-4">
        <Card>
          <CardHeader>
            <CardTitle>Cambios detectados</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {changes.isLoading ? <LoadingState label="Cargando cambios…" /> : null}
            {changes.isError ? <ErrorState error={changes.error} /> : null}
            {changes.data && changes.data.length === 0 ? (
              <EmptyState
                title="Sin cambios por encima del umbral"
                description="El trabajo puede haber terminado sin regiones que superen el umbral configurado."
              />
            ) : null}
            <ul className="flex flex-col gap-1">
              {changes.data?.map((change) => (
                <li key={change.id}>
                  <button
                    type="button"
                    onClick={() => {
                      selectChange(change.id);
                      setClosedPopup(false);
                    }}
                    className={`w-full rounded-md border px-2 py-1.5 text-left text-xs transition-colors ${
                      selected?.id === change.id
                        ? "border-accent/60 bg-accent/10 text-accent"
                        : "border-surface-border/70 hover:bg-surface-border/50"
                    }`}
                  >
                    <span className="block font-medium">{formatArea(change.area_km2)}</span>
                    <span className="block text-muted">
                      score {formatNumber(change.change_score, 3)} · {change.change_type}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        {selected ? (
          <Card>
            <CardHeader>
              <CardTitle>Métricas</CardTitle>
            </CardHeader>
            <CardContent>
              <ChangeMetrics changeId={selected.id} />
            </CardContent>
          </Card>
        ) : null}
      </aside>
    </div>
  );
}
