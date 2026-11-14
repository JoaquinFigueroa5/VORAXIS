import type { FeatureCollection } from "geojson";
import { Map as MapLibreMap, NavigationControl } from "maplibre-gl";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import "maplibre-gl/dist/maplibre-gl.css";

import { MapControls } from "@/components/map/MapControls";
import { addLayersOnce, fitToCollection, setGeoJsonSource } from "@/utils/map";
import { cn } from "@/utils/formatters";

const MAP_STYLE = "https://demotiles.maplibre.org/style.json";

export const MapContext = createContext<MapLibreMap | null>(null);

export function useMapInstance(): MapLibreMap | null {
  return useContext(MapContext);
}

interface EarthMapProps {
  aoi?: FeatureCollection;
  footprints?: FeatureCollection;
  fitTo?: FeatureCollection;
  className?: string;
  initialCenter?: [number, number];
  initialZoom?: number;
  children?: ReactNode;
}

/**
 * MapLibre shell. Child layer components read the map instance from context and
 * add their own sources/layers, so the map is the layout anchor of every page.
 */
export function EarthMap({
  aoi,
  footprints,
  fitTo,
  className,
  initialCenter = [0, 10],
  initialZoom = 2,
  children,
}: EarthMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const initial = useRef({ center: initialCenter, zoom: initialZoom });
  const [map, setMap] = useState<MapLibreMap | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const instance = new MapLibreMap({
      container,
      style: MAP_STYLE,
      center: initial.current.center,
      zoom: initial.current.zoom,
      attributionControl: false,
    });
    instance.addControl(new NavigationControl({ showCompass: false }), "top-right");
    instance.on("load", () => setMap(instance));

    return () => {
      instance.remove();
      setMap(null);
    };
  }, []);

  useEffect(() => {
    if (!map || !aoi) return;
    setGeoJsonSource(map, "aoi-src", aoi);
    addLayersOnce(map, [
      {
        id: "aoi-fill",
        type: "fill",
        source: "aoi-src",
        paint: { "fill-color": "#38bdf8", "fill-opacity": 0.08 },
      },
      {
        id: "aoi-line",
        type: "line",
        source: "aoi-src",
        paint: { "line-color": "#38bdf8", "line-width": 2 },
      },
    ]);
  }, [map, aoi]);

  useEffect(() => {
    if (!map || !fitTo) return;
    fitToCollection(map, fitTo, 90);
  }, [map, fitTo]);

  useEffect(() => {
    if (!map || !footprints) return;
    setGeoJsonSource(map, "footprints-src", footprints);
    addLayersOnce(map, [
      {
        id: "footprints-line",
        type: "line",
        source: "footprints-src",
        paint: { "line-color": "#94a3b8", "line-width": 1, "line-dasharray": [2, 2] },
      },
    ]);
  }, [map, footprints]);

  return (
    <div className={cn("relative h-full w-full overflow-hidden", className)}>
      <div ref={containerRef} className="absolute inset-0" aria-label="Mapa de cambios NISAR" />
      {map ? (
        <MapContext.Provider value={map}>
          <MapControls map={map} />
          {children}
        </MapContext.Provider>
      ) : (
        <div className="absolute inset-0 grid place-items-center text-sm text-muted">
          Cargando mapa…
        </div>
      )}
    </div>
  );
}
