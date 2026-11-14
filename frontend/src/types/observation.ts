export type StorageStatus = "DISCOVERED" | "READY" | "FAILED";

export interface Observation {
  id: string;
  scene_id: string;
  location_id: string | null;
  acquisition_date: string;
  processing_version: string | null;
  storage_status: StorageStatus;
  created_at: string;
}
