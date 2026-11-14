import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { ChangeTimeline } from "@/components/analysis/ChangeTimeline";
import { AuxiliaryLayers } from "@/components/map/AuxiliaryLayers";
import { ChangeLayer } from "@/components/map/ChangeLayer";
import { EarthMap } from "@/components/map/EarthMap";
import { MapLegend } from "@/components/map/MapLegend";
import { EvidencePanel } from "@/components/evidence/EvidencePanel";
import { EvidenceTimeline } from "@/components/evidence/EvidenceTimeline";
import { ExplanationPanel } from "@/components/evidence/ExplanationPanel";
import { ChangeDistribution } from "@/components/insights/ChangeDistribution";
import { InsightsSummary } from "@/components/insights/InsightsSummary";
import { TrendChart } from "@/components/insights/TrendChart";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useChange } from "@/hooks/useChanges";
import { useEvidence, useAuxiliaryEvents } from "@/hooks/useEvidence";
import { changesService } from "@/services/changes.service";
import { insightsService } from "@/services/insights.service";
import {
  auxiliaryToFeatureCollection,
  changesToFeatureCollection,
} from "@/utils/geometry";
import { formatArea, formatNumber } from "@/utils/formatters";

export function InsightsPage() {
  const { id } = useParams<{ id: string }>();
  return id ? <ChangeInsights changeId={id} /> : <GlobalInsights />;
}

function GlobalInsights() {
  const summary = useQuery({ queryKey: ["insights"], queryFn: insightsService.summary });
  const changes = useQuery({
    queryKey: ["changes", "all"],
    queryFn: () => changesService.list({ limit: 100 }),
  });
  const auxiliary = useAuxiliaryEvents();

  if (summary.isLoading) return <LoadingState label="Agregando estadísticas…" />;
  if (summary.isError) return <div className="p-4"><ErrorState error={summary.error} /></div>;

  const changeData = changes.data ?? [];
  const auxiliaryData = auxiliary.data ?? [];

  return (
    <div className="grid h-full min-h-0 grid-cols-1 overflow-y-auto lg:grid-cols-[420px_1fr] lg:overflow-hidden">
      <aside className="flex min-h-0 flex-col gap-3 overflow-y-auto p-4">
        {summary.data ? <InsightsSummary summary={summary.data} /> : null}

        <Card>
          <CardHeader>
            <CardTitle>Estados de los trabajos</CardTitle>
          </CardHeader>
          <CardContent>
            {summary.data ? <TrendChart jobs={summary.data.jobs} /> : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Área de los cambios</CardTitle>
          </CardHeader>
          <CardContent>
            <ChangeDistribution changes={changeData} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Cambios recientes</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            {changeData.length === 0 ? (
              <EmptyState
                title="Sin cambios registrados"
                description="Ejecuta un análisis GCOV para poblar esta vista."
              />
            ) : null}
            {changeData.slice(0, 8).map((change) => (
              <Link
                key={change.id}
                to={`/insights/${change.id}`}
                className="flex items-center justify-between rounded-md border border-surface-border/70 px-2 py-1.5 text-xs text-slate-200 hover:bg-surface-border/50"
              >
                <span>{formatArea(change.area_km2)}</span>
                <span className="text-muted">score {formatNumber(change.change_score, 3)}</span>
              </Link>
            ))}
          </CardContent>
        </Card>
      </aside>

      <div className="relative min-h-[360px]">
        <EarthMap
          fitTo={
            changeData.length > 0
              ? changesToFeatureCollection(changeData)
              : auxiliaryData.length > 0
                ? auxiliaryToFeatureCollection(auxiliaryData)
                : undefined
          }
          initialCenter={[-90.2, 16.8]}
          initialZoom={5}
        >
          <ChangeLayer data={changesToFeatureCollection(changeData)} />
          <AuxiliaryLayers data={auxiliaryToFeatureCollection(auxiliaryData)} />
        </EarthMap>
        <MapLegend />
      </div>
    </div>
  );
}

function ChangeInsights({ changeId }: { changeId: string }) {
  const change = useChange(changeId);
  const evidence = useEvidence(changeId);
  const auxiliary = useAuxiliaryEvents();

  if (change.isLoading) return <LoadingState label="Cargando cambio…" />;
  if (change.isError) return <div className="p-4"><ErrorState error={change.error} /></div>;
  if (!change.data) return null;

  const records = evidence.data ?? [];

  return (
    <div className="grid h-full min-h-0 grid-cols-1 overflow-y-auto lg:grid-cols-[420px_1fr] lg:overflow-hidden">
      <aside className="flex min-h-0 flex-col gap-3 overflow-y-auto p-4">
        <ExplanationPanel change={change.data} records={records} />

        <Card>
          <CardHeader>
            <CardTitle>Detalle del cambio</CardTitle>
          </CardHeader>
          <CardContent>
            <ChangeTimeline />
            <dl className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div>
                <dt className="text-muted">Área</dt>
                <dd className="text-slate-100">{formatArea(change.data.area_km2)}</dd>
              </div>
              <div>
                <dt className="text-muted">Score relativo</dt>
                <dd className="text-slate-100">{formatNumber(change.data.change_score, 3)}</dd>
              </div>
              <div>
                <dt className="text-muted">Tipo</dt>
                <dd className="text-slate-100">{change.data.change_type}</dd>
              </div>
              <div>
                <dt className="text-muted">Trabajo</dt>
                <dd className="truncate text-slate-100">{change.data.job_id.slice(0, 8)}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <EvidencePanel changeId={changeId} />

        <Card>
          <CardHeader>
            <CardTitle>Eventos en el tiempo</CardTitle>
          </CardHeader>
          <CardContent>
            {records.length > 0 ? (
              <EvidenceTimeline records={records} />
            ) : (
              <p className="text-xs text-muted">Sin eventos relacionados.</p>
            )}
          </CardContent>
        </Card>
      </aside>

      <div className="relative min-h-[360px]">
        <EarthMap
          fitTo={changesToFeatureCollection([change.data])}
          initialCenter={[-90.2, 16.8]}
          initialZoom={9}
        >
          <ChangeLayer data={changesToFeatureCollection([change.data])} />
          <AuxiliaryLayers data={auxiliaryToFeatureCollection(auxiliary.data ?? [])} />
        </EarthMap>
        <MapLegend />
      </div>
    </div>
  );
}
