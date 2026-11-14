import type { Feature, FeatureCollection, Geometry, MultiPolygon, Position } from "geojson";
import type { ChangeEvent } from "@/types/change";
import type { AuxiliaryEvent } from "@/types/evidence";
import type { Location } from "@/types/location";
import type { NisarScene } from "@/types/nisar";

export type BBox = [number, number, number, number];

function walkCoordinates(geometry: Geometry, visit: (position: Position) => void): void {
  const walk = (value: unknown): void => {
    if (!Array.isArray(value)) return;
    if (typeof value[0] === "number" && typeof value[1] === "number") {
      visit(value as Position);
      return;
    }
    value.forEach(walk);
  };
  walk(geometry.type === "GeometryCollection" ? geometry.geometries : geometry.coordinates);
}

export function computeBbox(geometry: Geometry): BBox {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  walkCoordinates(geometry, ([x, y]) => {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  });

  return [minX, minY, maxX, maxY];
}

export function bboxToString(bbox: BBox): string {
  return bbox.join(",");
}

export function geometryCenter(geometry: Geometry): [number, number] {
  const [minX, minY, maxX, maxY] = computeBbox(geometry);
  return [(minX + maxX) / 2, (minY + maxY) / 2];
}

function collection(features: Feature[]): FeatureCollection {
  return { type: "FeatureCollection", features };
}

export function locationsToFeatureCollection(locations: Location[]): FeatureCollection {
  return collection(
    locations.map((location) => ({
      type: "Feature",
      id: location.id,
      geometry: location.geometry,
      properties: { id: location.id, name: location.name, country: location.country },
    })),
  );
}

export function scenesToFeatureCollection(scenes: NisarScene[]): FeatureCollection {
  return collection(
    scenes.map((scene) => ({
      type: "Feature",
      id: scene.id,
      geometry: scene.footprint,
      properties: {
        id: scene.id,
        product_id: scene.product_id,
        product_type: scene.product_type,
        acquisition_start: scene.acquisition_start,
      },
    })),
  );
}

export function changesToFeatureCollection(changes: ChangeEvent[]): FeatureCollection {
  return collection(
    changes.map((change) => ({
      type: "Feature",
      id: change.id,
      geometry: change.geometry,
      properties: {
        id: change.id,
        change_type: change.change_type,
        area_km2: change.area_km2,
        change_score: change.change_score,
      },
    })),
  );
}

export function auxiliaryToFeatureCollection(events: AuxiliaryEvent[]): FeatureCollection {
  return collection(
    events.map((event) => ({
      type: "Feature",
      id: event.id,
      geometry: event.geometry,
      properties: {
        id: event.id,
        source: event.source,
        event_type: event.event_type,
        event_date: event.event_date,
        magnitude: event.magnitude,
      },
    })),
  );
}

export function multiPolygonCenter(geometry: MultiPolygon): [number, number] {
  return geometryCenter(geometry);
}
