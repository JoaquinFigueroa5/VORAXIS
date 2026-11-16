import type { Coded } from "@/i18n";
import type { ChangeDirection } from "@/types/change";
import type { EvidenceRecord } from "@/types/evidence";

export type SourceStatus = "AVAILABLE" | "UNAVAILABLE" | "NOT_CONFIGURED";

/** GET /changes/{id}/interpretation: what was measured, not what one wishes it meant. */
export interface Interpretation {
  change_id: string;
  job_id: string;
  /** COMPLETE only when every source answered and the change is classified */
  status: "COMPLETE" | "PARTIAL";
  location: { id: string; name: string; country: string | null } | null;
  period: { before: string | null; after: string | null; interval_days: number | null };
  observation: {
    product_id: string | null;
    product_type: string | null;
    maturity: string | null;
    polarization: string[] | null;
    orbit_direction: string | null;
    processing_version: string | null;
  };
  change: {
    change_type: string;
    area_km2: number | null;
    change_score: number | null;
    valid_pixel_percentage: number | null;
    direction: ChangeDirection | null;
    mean_change_db: number | null;
  };
  classification: { confidence: "NONE" | "LOW" | "MEDIUM" | null; reasons: Coded[] };
  metrics: { name: string; value: number | null; unit: string | null }[];
  evidence: EvidenceRecord[];
  /** NISAR first, then whichever auxiliary sources the job tried */
  sources: Record<string, { status: SourceStatus; events_found: number | null; detail: string | null; code: string | null }>;
  /** `limitation.<code>` in the dictionaries */
  limitations: Coded[];
}
