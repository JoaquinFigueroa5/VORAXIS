import type { MultiPolygon } from "geojson";

export interface Location {
  id: string;
  name: string;
  country: string | null;
  description: string | null;
  geometry: MultiPolygon;
  created_at: string;
}
