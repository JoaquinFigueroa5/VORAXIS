import type { Geometry } from "geojson";

export type AuxiliarySource = "USGS" | "FIRMS" | "POWER";

export interface AuxiliaryEvent {
  id: string;
  source: string;
  external_id: string | null;
  event_type: string;
  event_date: string;
  geometry: Geometry;
  magnitude: number | null;
  metadata: Record<string, unknown> | null;
}

export interface EvidenceRecord {
  id: string;
  change_event_id: string;
  auxiliary_event_id: string;
  spatial_relation: "INTERSECTS" | "NEAR" | "WITHIN" | string;
  distance_km: number | null;
  time_difference_hours: number | null;
  evidence_score: number | null;
  created_at: string;
  event: AuxiliaryEvent | null;
}
