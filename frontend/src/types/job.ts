export type JobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";

export type JobStep =
  | "DOWNLOADING"
  | "PREPROCESSING"
  | "ALIGNMENT"
  | "CHANGE_DETECTION"
  | "VECTORIZATION"
  | "EVIDENCE_ANALYSIS"
  | "EXPORTING"
  | "DONE";

export interface ProcessingJob {
  id: string;
  location_id: string;
  before_observation_id: string;
  after_observation_id: string;
  status: JobStatus;
  progress: number;
  current_step: JobStep | null;
  error_message: string | null;
  /** Parameters the analysis was requested with */
  parameters: Record<string, unknown> | null;
  /** Threshold, counts per change_type and status of each auxiliary source */
  result: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export const FINAL_JOB_STATUSES: JobStatus[] = ["COMPLETED", "FAILED", "CANCELLED"];
