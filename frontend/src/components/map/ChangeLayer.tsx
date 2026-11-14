import type { FeatureCollection } from "geojson";
import type { LayerSpecification } from "maplibre-gl";
import { useEffect } from "react";

import { useMapInstance } from "@/components/map/EarthMap";
import { addLayersOnce, removeSourceAndLayers, setGeoJsonSource } from "@/utils/map";

export const CHANGES_SOURCE = "changes-src";

const LAYERS: LayerSpecification[] = [
  {
    id: "changes-fill",
    type: "fill",
    source: CHANGES_SOURCE,
    paint: { "fill-color": "#f97316", "fill-opacity": 0.35 },
  },
  {
    id: "changes-outline",
    type: "line",
    source: CHANGES_SOURCE,
    paint: { "line-color": "#fb923c", "line-width": 1.5 },
  },
];

export function ChangeLayer({ data }: { data: FeatureCollection }) {
  const map = useMapInstance();

  useEffect(() => {
    if (!map) return;
    setGeoJsonSource(map, CHANGES_SOURCE, data);
    addLayersOnce(map, LAYERS);

    return () => removeSourceAndLayers(map, CHANGES_SOURCE, LAYERS.map((layer) => layer.id));
  }, [map, data]);

  return null;
}
