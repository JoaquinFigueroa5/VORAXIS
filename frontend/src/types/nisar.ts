import type { MultiPolygon } from "geojson";

export type ProductType = "GCOV" | "GUNW" | "GOFF" | "SME2";

export interface NisarScene {
  id: string;
  product_id: string;
  product_type: string;
  maturity: string | null;
  acquisition_start: string;
  acquisition_end: string | null;
  orbit_direction: string | null;
  polarization: string[] | null;
  footprint: MultiPolygon;
  source_url: string | null;
  metadata: Record<string, unknown> | null;
  discovered_at: string;
}

export interface SceneFilters {
  product_type?: string;
  maturity?: string;
  start?: string;
  end?: string;
  bbox?: string;
  limit?: number;
  offset?: number;
}
