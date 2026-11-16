import type { Coded } from "@/i18n";
import { z } from "zod";

export const analysisParametersSchema = z.object({
  polarization: z.string().min(1, "Polarización requerida"),
  minimum_valid_pixel_percentage: z.number().min(0).max(100),
  change_threshold_sigma: z.number().gt(0).max(10),
  // Optional: the API applies its defaults when they are omitted.
  smoothing_window: z.number().int().min(1).max(31).optional(),
  noise_floor_db: z.number().min(-60).max(0).nullable().optional(),
  edge_buffer_pixels: z.number().int().min(0).max(200).optional(),
  minimum_area_km2: z.number().min(0).max(100).optional(),
  fetch_auxiliary: z.boolean().optional(),
});

export const analysisRequestSchema = z.object({
  location_id: z.string().min(1, "Selecciona una región"),
  before_observation_id: z.string().min(1, "Selecciona la observación inicial"),
  after_observation_id: z.string().min(1, "Selecciona la observación final"),
  analysis_type: z.literal("GCOV_CHANGE"),
  parameters: analysisParametersSchema,
});

export type AnalysisRequest = z.infer<typeof analysisRequestSchema>;
export type AnalysisParameters = z.infer<typeof analysisParametersSchema>;

export interface AnalysisAccepted {
  job_id: string;
  status: string;
  progress: number;
  /** The pair is usable, but the user should see these (`job.warning.<code>`) */
  warnings: Coded[];
}

export interface InsightsSummary {
  locations: number;
  scenes: number;
  observations: number;
  jobs: Record<string, number>;
  change_events: number;
  change_area_km2: number;
  evidence_records: number;
  auxiliary_events: number;
  /** Distributions across every analysis. Empty until something has been detected. */
  by_type: { change_type: string; count: number; area_km2: number }[];
  by_direction: { direction: "DECREASE" | "INCREASE" | null; count: number; area_km2: number }[];
  by_month: { month: string; count: number; area_km2: number }[];
  by_location: { location_id: string; name: string; count: number; area_km2: number }[];
}

/** GET /jobs/{id}/insights: aggregates for the charts of one analysis. */
export interface JobInsights {
  job_id: string;
  status: string;
  acquisitions: { before: string | null; after: string | null };
  totals: {
    changes: number;
    area_km2: number;
    mean_score: number | null;
    max_score: number | null;
    largest_km2: number | null;
    threshold_db: number | null;
    /** Of the area both dates observe */
    valid_pixel_percentage: number | null;
    /** Of the whole area of interest */
    aoi_coverage_percentage: number | null;
  };
  by_type: {
    change_type: string;
    count: number;
    area_km2: number;
    mean_score: number | null;
    mean_change_db: number | null;
  }[];
  by_direction: { direction: "DECREASE" | "INCREASE" | null; count: number; area_km2: number }[];
  score_histogram: { from: number; to: number; count: number }[];
  /** `to_km2` is null for the last, open-ended bin */
  area_histogram: { from_km2: number; to_km2: number | null; count: number; area_km2: number }[];
  evidence: {
    event_type: string;
    source: string;
    events: number;
    links: number;
    best_score: number | null;
  }[];
  precipitation: {
    cell_center: { longitude: number; latitude: number };
    total_mm: number | null;
    expected_mm: number | null;
    anomaly_pct: number | null;
    max_daily_mm: number | null;
    peak_date: string | null;
    series: { date: string; mm: number | null }[];
  }[];
  sources: Record<string, { status: "ok" | "skipped" | "error"; events_found?: number; detail?: string }>;
  warnings: Coded[];
}
