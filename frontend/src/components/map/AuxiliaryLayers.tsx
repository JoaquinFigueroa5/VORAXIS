import type { FeatureCollection } from "geojson";
import type { LayerSpecification } from "maplibre-gl";
import { useEffect } from "react";

import { useMapInstance } from "@/components/map/EarthMap";
import { addLayersOnce, removeSourceAndLayers, setGeoJsonSource } from "@/utils/map";

const SOURCE = "auxiliary-src";

const LAYERS: LayerSpecification[] = [
  {
    id: "auxiliary-circle",
    type: "circle",
    source: SOURCE,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 3, 10, 7],
      "circle-color": [
        "match",
        ["get", "event_type"],
        "EARTHQUAKE",
        "#f59e0b",
        "FIRE",
        "#ef4444",
        "PRECIPITATION",
        "#22d3ee",
        "#a78bfa",
      ],
      "circle-stroke-color": "#0b1220",
      "circle-stroke-width": 1,
      "circle-opacity": 0.85,
    },
  },
];

export function AuxiliaryLayers({ data }: { data: FeatureCollection }) {
  const map = useMapInstance();

  useEffect(() => {
    if (!map) return;
    setGeoJsonSource(map, SOURCE, data);
    addLayersOnce(map, LAYERS);

    return () => removeSourceAndLayers(map, SOURCE, LAYERS.map((layer) => layer.id));
  }, [map, data]);

  return null;
}
