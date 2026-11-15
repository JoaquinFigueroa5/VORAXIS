export type IngestStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";
export type IngestStage = "QUEUED" | "DOWNLOADING" | "CONVERTING" | "UPLOADING" | "READY";

/** POST /ingest: one task is queued per product. */
export type IngestRequest = {
  location_id: string;
  /** Granule names from /context/nisar, e.g. both sides of a comparable pair */
  product_ids: string[];
  polarizations?: string[];
  /** 4 = 40 m pixels; use the same value for both dates of a pair */
  multilook?: number;
  force?: boolean;
};

export interface IngestTask {
  id: string;
  product_id: string | null;
  location_id: string | null;
  status: IngestStatus;
  stage: IngestStage | null;
  /** 0-100 */
  progress: number;
  /** e.g. "1.80 GB de 4.89 GB" while downloading */
  detail: string | null;
  /** Present when COMPLETED; `observation_id` is what POST /analysis needs */
  result: {
    observation_id: string;
    scene_id: string;
    asset_id: string;
    product_id: string;
    storage_path: string;
    crs: string | null;
    skipped: boolean;
  } | null;
  error: string | null;
  enqueued_at: string | null;
  started_at: string | null;
  ended_at: string | null;
}

export const FINAL_INGEST_STATUSES: IngestStatus[] = ["COMPLETED", "FAILED"];
