import type { Coded } from "@/i18n";
import type { FeatureCollection, MultiPolygon } from "geojson";

export type ChangeDirection = "DECREASE" | "INCREASE";

export interface ChangeEvent {
  id: string;
  job_id: string;
  change_type: string;
  geometry: MultiPolygon;
  area_km2: number | null;
  change_score: number | null;
  valid_pixel_percentage: number | null;
  /** DECREASE = darker surface, INCREASE = brighter */
  direction: ChangeDirection | null;
  /** Signed mean backscatter change in dB */
  mean_change_db: number | null;
  /** Why the classifier said so. Tentative: `confidence` is LOW/MEDIUM/NONE, never a probability. */
  classification: ChangeClassification | null;
  created_at: string;
}

export interface ChangeClassification {
  type: string;
  confidence: "NONE" | "LOW" | "MEDIUM" | null;
  /** `reason.<code>` in the dictionaries */
  reasons: Coded[];
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

/** Filters shared by the change list and the GeoJSON layer. */
export type ChangeFilters = {
  job_id?: string;
  bbox?: string;
  /** One or more of POSSIBLE_FLOODING, POSSIBLE_BURN_SCAR, UNCLASSIFIED... */
  change_type?: string[];
  direction?: ChangeDirection;
  min_score?: number;
  min_area_km2?: number;
  sort?: "area" | "score" | "newest";
};

export interface ChangeProperties {
  id: string;
  job_id: string;
  change_type: string;
  /** Spanish, ready to display */
  label: string;
  direction: ChangeDirection | null;
  change_score: number | null;
  area_km2: number | null;
  mean_change_db: number | null;
}

/** GET /changes/geojson */
export interface ChangeCollection extends FeatureCollection<MultiPolygon, ChangeProperties> {
  /** How many changes match the filters */
  numberMatched: number;
  /** How many came back (capped by `limit`, or simplified away at low zoom) */
  numberReturned: number;
}

export interface ChangePage {
  items: ChangeEvent[];
  /** Total matching the filters, from the X-Total-Count header */
  total: number;
}
