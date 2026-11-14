import { z } from "zod";

export const analysisParametersSchema = z.object({
  polarization: z.string().min(1, "Polarización requerida"),
  minimum_valid_pixel_percentage: z.number().min(0).max(100),
  change_threshold_sigma: z.number().gt(0).max(10),
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
  message: string;
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
}
