import { Crosshair, Minus, Plus } from "lucide-react";
import type { Map as MapLibreMap } from "maplibre-gl";

import { Button } from "@/components/ui/button";
import { useMapStore } from "@/stores/map.store";

export function MapControls({ map }: { map: MapLibreMap }) {
  const { center, zoom } = useMapStore();

  return (
    <div className="absolute bottom-4 left-4 z-10 flex flex-col gap-1 rounded-md border border-surface-border bg-surface-raised/90 p-1">
      <Button
        variant="ghost"
        size="icon"
        aria-label="Acercar"
        onClick={() => map.zoomIn()}
        className="h-8 w-8"
      >
        <Plus className="h-4 w-4" aria-hidden />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        aria-label="Alejar"
        onClick={() => map.zoomOut()}
        className="h-8 w-8"
      >
        <Minus className="h-4 w-4" aria-hidden />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        aria-label="Volver a la vista inicial"
        onClick={() => map.flyTo({ center, zoom, duration: 700 })}
        className="h-8 w-8"
      >
        <Crosshair className="h-4 w-4" aria-hidden />
      </Button>
    </div>
  );
}
