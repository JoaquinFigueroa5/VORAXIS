import { apiFetch, buildQuery } from "@/services/api";
import type { IngestRequest, IngestTask } from "@/types/ingest";

/**
 * Download NISAR products and prepare them for analysis. Tasks run one at a
 * time on the worker; poll `get` until the status is COMPLETED or FAILED
 * (a real download takes several minutes per product).
 */
export const ingestService = {
  create: (request: IngestRequest) =>
    apiFetch<IngestTask[]>("/ingest", { method: "POST", body: JSON.stringify(request) }),
  get: (id: string) => apiFetch<IngestTask>(`/ingest/${id}`),
  /** Queued, running and recently finished tasks (kept for 24 h), newest first. */
  list: (params: { location_id?: string; limit?: number } = {}) =>
    apiFetch<IngestTask[]>(`/ingest${buildQuery(params)}`),
};
