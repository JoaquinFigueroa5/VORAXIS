import { MapPinned } from "lucide-react";
import { useState } from "react";

import { AnalysisPanel } from "@/components/analysis/AnalysisPanel";
import { DateRangeSelector } from "@/components/analysis/DateRangeSelector";
import { AOIDrawer } from "@/components/map/AOIDrawer";
import { EarthMap } from "@/components/map/EarthMap";
import { MapLegend } from "@/components/map/MapLegend";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocations } from "@/hooks/useLocations";
import { useNisarScenes } from "@/hooks/useNisarScenes";
import { useObservations } from "@/hooks/useObservations";
import { useFiltersStore } from "@/stores/filters.store";
import { useMapStore } from "@/stores/map.store";
import { bboxToString, computeBbox, locationsToFeatureCollection, scenesToFeatureCollection } from "@/utils/geometry";
import { formatDateTime } from "@/utils/formatters";

export function ExplorerPage() {
  const locations = useLocations();
  const selectedId = useMapStore((state) => state.selectedLocationId);
  const selectLocation = useMapStore((state) => state.selectLocation);
  const { startDate, endDate, productType } = useFiltersStore();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const selected = locations.data?.find((location) => location.id === selectedId) ?? null;
  const bbox = selected ? bboxToString(computeBbox(selected.geometry)) : undefined;

  const scenes = useNisarScenes({
    start: startDate,
    end: endDate,
    product_type: productType || undefined,
    bbox,
    limit: 100,
  });
  const observations = useObservations({ location_id: selectedId ?? undefined });

  const aoi = selected ? locationsToFeatureCollection([selected]) : undefined;
  const footprints = scenes.data ? scenesToFeatureCollection(scenes.data) : undefined;

  return (
    <div className="grid h-full min-h-0 grid-cols-1 lg:grid-cols-[380px_1fr]">
      <aside className="flex min-h-0 flex-col gap-3 overflow-y-auto border-r border-surface-border p-4">
        <Button variant="secondary" onClick={() => setDrawerOpen(true)}>
          <MapPinned className="h-4 w-4" aria-hidden />
          {selected ? `${selected.name} · ${selected.country ?? "—"}` : "Seleccionar región"}
        </Button>

        <Card>
          <CardHeader>
            <CardTitle>Filtros del catálogo</CardTitle>
          </CardHeader>
          <CardContent>
            <DateRangeSelector />
          </CardContent>
        </Card>

        {locations.isError ? <ErrorState error={locations.error} /> : null}
        {scenes.isError ? <ErrorState error={scenes.error} /> : null}

        <Card>
          <CardHeader>
            <CardTitle>Escenas encontradas</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <p className="text-xs text-muted">
              {scenes.data?.length ?? 0} escenas · {observations.data?.length ?? 0} observaciones
              preparadas
            </p>
            {selected && (scenes.data?.length ?? 0) === 0 ? (
              <EmptyState
                title="Sin escenas en el catálogo"
                description="Sincroniza ASF para esta AOI y rango de fechas con scripts/sync_nisar_catalog.py."
              />
            ) : null}
            <ul className="flex flex-col gap-1">
              {scenes.data?.slice(0, 6).map((scene) => (
                <li
                  key={scene.id}
                  className="rounded-md border border-surface-border/70 px-2 py-1.5 text-xs"
                >
                  <p className="font-medium text-slate-200">
                    {scene.product_type} · {scene.maturity ?? "—"}
                  </p>
                  <p className="text-muted">{formatDateTime(scene.acquisition_start)}</p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <AnalysisPanel locationId={selectedId} />
      </aside>

      <div className="relative min-h-[320px]">
        <EarthMap
          aoi={aoi}
          footprints={footprints}
          fitTo={footprints?.features.length ? footprints : aoi}
          initialCenter={[-90.2, 16.8]}
          initialZoom={7}
        />
        <MapLegend />
      </div>

      <AOIDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        locations={locations.data ?? []}
        selectedId={selectedId}
        onSelect={(location) => selectLocation(location.id)}
      />
    </div>
  );
}
