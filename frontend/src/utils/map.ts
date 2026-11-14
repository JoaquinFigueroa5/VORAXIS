import type { FeatureCollection } from "geojson";
import type { GeoJSONSource, LayerSpecification, Map as MapLibreMap } from "maplibre-gl";

export function setGeoJsonSource(
  map: MapLibreMap,
  sourceId: string,
  data: FeatureCollection,
): void {
  const existing = map.getSource(sourceId) as GeoJSONSource | undefined;
  if (existing) {
    existing.setData(data);
    return;
  }
  map.addSource(sourceId, { type: "geojson", data });
}

export function addLayersOnce(map: MapLibreMap, layers: LayerSpecification[]): void {
  for (const layer of layers) {
    if (!map.getLayer(layer.id)) {
      map.addLayer(layer);
    }
  }
}

export function removeSourceAndLayers(
  map: MapLibreMap,
  sourceId: string,
  layerIds: string[],
): void {
  for (const id of layerIds) {
    if (map.getLayer(id)) map.removeLayer(id);
  }
  if (map.getSource(sourceId)) map.removeSource(sourceId);
}

/** Fit the map to every coordinate in a collection, padding for the side panel. */
export function fitToCollection(
  map: MapLibreMap,
  data: FeatureCollection,
  padding = 80,
): void {
  if (data.features.length === 0) return;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  const visit = (value: unknown): void => {
    if (!Array.isArray(value)) return;
    if (typeof value[0] === "number" && typeof value[1] === "number") {
      minX = Math.min(minX, value[0]);
      minY = Math.min(minY, value[1]);
      maxX = Math.max(maxX, value[0]);
      maxY = Math.max(maxY, value[1]);
      return;
    }
    value.forEach(visit);
  };

  for (const feature of data.features) {
    const geometry = feature.geometry;
    if (geometry.type === "GeometryCollection") {
      geometry.geometries.forEach((child) =>
        visit(child.type === "GeometryCollection" ? child.geometries : child.coordinates),
      );
    } else {
      visit(geometry.coordinates);
    }
  }

  if (!Number.isFinite(minX)) return;
  map.fitBounds(
    [
      [minX, minY],
      [maxX, maxY],
    ],
    { padding, duration: 600, maxZoom: 11 },
  );
}
