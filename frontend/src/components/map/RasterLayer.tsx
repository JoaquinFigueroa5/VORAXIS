import { useEffect } from "react";

import { useMapInstance } from "@/components/map/EarthMap";

const SOURCE = "raster-src";
const LAYER = "raster-layer";

/**
 * XYZ raster layer for before/after/difference. The backend still answers 501 for
 * tile routes, so callers pass `undefined` and nothing is drawn.
 */
export function RasterLayer({ tilesUrl, opacity = 0.75 }: { tilesUrl?: string; opacity?: number }) {
  const map = useMapInstance();

  useEffect(() => {
    if (!map || !tilesUrl) return;

    if (!map.getSource(SOURCE)) {
      map.addSource(SOURCE, {
        type: "raster",
        tiles: [tilesUrl],
        tileSize: 256,
        attribution: "NISAR",
      });
    }
    if (!map.getLayer(LAYER)) {
      map.addLayer({
        id: LAYER,
        type: "raster",
        source: SOURCE,
        paint: { "raster-opacity": opacity },
      });
    }

    return () => {
      if (map.getLayer(LAYER)) map.removeLayer(LAYER);
      if (map.getSource(SOURCE)) map.removeSource(SOURCE);
    };
  }, [map, tilesUrl, opacity]);

  return null;
}
