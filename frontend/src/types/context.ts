import type { Geometry } from "geojson";

/** Shared by every /context/* response: where the data came from and when. */
interface Provenance {
  source: string;
  endpoint: string | null;
  retrieved_at: string;
  query: Record<string, string | number>;
}

export interface NisarGranule {
  product_id: string;
  level: string;
  track: number | null;
  frame: number | null;
  flight_direction: string | null;
  polarization: string[] | null;
  /** PROVISIONAL, BETA... as ASF reports it */
  maturity: string | null;
  processing_version: string | null;
  start: string;
  stop: string | null;
  age_days: number | null;
  size_gb: number | null;
  browse_png: string | null;
  download_url: string | null;
  footprint: Geometry | null;
}

/** Two GCOV dates of the same track and frame: a before/after pair ready to analyse. */
export interface NisarPair {
  track: number;
  frame: number;
  flight_direction: string;
  polarization: string[];
  /** Both sides share it: ingestion refuses a pair that mixes maturities */
  maturity: string | null;
  before: { product_id: string; start: string };
  after: { product_id: string; start: string };
  interval_days: number;
  same_processing_version: boolean;
  download_gb: number;
}

export interface NisarContext extends Provenance {
  total: number;
  truncated: boolean;
  count_by_level: Record<string, number>;
  latest_by_level: Record<string, { product_id: string; start: string; age_days: number | null }>;
  has_gcov: boolean;
  comparable_pairs: NisarPair[];
  granules: NisarGranule[];
}

export interface Earthquake {
  id: string;
  time: string;
  magnitude: number | null;
  depth_km: number | null;
  place: string | null;
  latitude: number;
  longitude: number;
  distance_km: number;
  url: string | null;
}

export interface EarthquakeContext extends Provenance {
  total: number;
  max_magnitude: number | null;
  nearest: Earthquake | null;
  strongest: Earthquake | null;
  data: Earthquake[];
}

export interface PrecipitationContext extends Provenance {
  /** false when NASA POWER has not published this window yet */
  available: boolean;
  units: string;
  grid: string;
  elevation_m?: number | null;
  total_mm?: number;
  expected_mm?: number | null;
  anomaly_pct?: number | null;
  max_daily_mm?: number;
  peak_date?: string;
  series: { date: string; mm: number | null }[];
}

export interface FireDetection {
  time: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  frp_mw: number | null;
  confidence: "low" | "nominal" | "high" | null;
  satellite: string | null;
  collection: string | null;
  daynight: string | null;
}

export interface FireContext extends Provenance {
  total: number;
  max_frp_mw: number | null;
  total_frp_mw: number;
  detections_by_day: Record<string, number>;
  data: FireDetection[];
}

export type TimelineKind = "nisar" | "earthquake" | "precipitation" | "fire";

export interface TimelineEvent {
  date: string;
  kind: TimelineKind;
  /** Spanish, ready to display */
  title: string;
  detail?: string | null;
  product_id?: string;
  browse_png?: string | null;
  magnitude?: number | null;
  distance_km?: number;
  latitude?: number;
  longitude?: number;
  mm?: number;
  detections?: number;
}

export interface TimelineContext {
  query: Record<string, string | number>;
  generated_at: string;
  total: number;
  count_by_kind: Record<TimelineKind, number>;
  sources: {
    source: string;
    status: "ok" | "error";
    events: number;
    retrieved_at?: string;
    endpoint?: string | null;
    detail?: string;
  }[];
  events: TimelineEvent[];
}

/** `days` = the last N days; `start`/`end` (YYYY-MM-DD) = a window in the past. */
export type ContextQuery = {
  lat: number;
  lon: number;
  days?: number;
  start?: string;
  end?: string;
};
