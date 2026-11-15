import type { MultiPolygon, Polygon } from "geojson";

export interface Location {
  id: string;
  name: string;
  country: string | null;
  description: string | null;
  geometry: MultiPolygon;
  created_at: string;
}

/** POST /locations: send exactly one of `geometry` or `bbox`. Max 3 degrees per side. */
export type LocationCreate = {
  name: string;
  country?: string;
  description?: string;
  geometry?: Polygon | MultiPolygon;
  /** [west, south, east, north] */
  bbox?: [number, number, number, number];
};
