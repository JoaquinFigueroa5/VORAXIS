export type StorageStatus = "DISCOVERED" | "READY" | "FAILED";

export interface Observation {
  id: string;
  scene_id: string;
  location_id: string | null;
  acquisition_date: string;
  processing_version: string | null;
  storage_status: StorageStatus;
  /** Copied from the scene so lists do not need a second request */
  product_id: string | null;
  product_type: string | null;
  maturity: string | null;
  orbit_direction: string | null;
  polarization: string[] | null;
  created_at: string;
}
