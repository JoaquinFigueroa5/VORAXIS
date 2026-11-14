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
