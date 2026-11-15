import type { MultiPolygon } from "geojson";

export interface ChangeEvent {
  id: string;
  job_id: string;
  change_type: string;
  geometry: MultiPolygon;
  area_km2: number | null;
  change_score: number | null;
  valid_pixel_percentage: number | null;
  created_at: string;
}

export interface ChangeMetric {
  id: string;
  change_event_id: string;
  metric_name: string;
  value: number | null;
  unit: string | null;
  source: string | null;
  metadata: Record<string, unknown> | null;
}

export type TileLayer = "before" | "after" | "difference" | "mask";

/** GET /changes/{id}/tiles or /jobs/{id}/tiles */
export interface TileDescription {
  job_id: string;
  status: string;
  tile_size: number;
  scheme: "xyz";
  /** [west, south, east, north] in EPSG:4326, or null while the job has no rasters */
  bounds: [number, number, number, number] | null;
  minzoom: number;
  maxzoom: number;
  polarization: string;
  /** Paths relative to the API origin, with {z}/{x}/{y} placeholders */
  layers: Partial<Record<TileLayer, string>>;
  legend: Record<string, Record<string, unknown>>;
}
