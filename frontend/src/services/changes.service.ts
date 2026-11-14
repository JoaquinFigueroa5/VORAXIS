import { API_URL, apiFetch, buildQuery } from "@/services/api";
import type { ChangeEvent, ChangeMetric } from "@/types/change";

export const changesService = {
  list: (params: { job_id?: string; bbox?: string; limit?: number } = {}) =>
    apiFetch<ChangeEvent[]>(`/changes${buildQuery({ ...params, limit: params.limit ?? 100 })}`),
  get: (id: string) => apiFetch<ChangeEvent>(`/changes/${id}`),
  metrics: (id: string) => apiFetch<ChangeMetric[]>(`/changes/${id}/metrics`),
  /** Tiles are not generated yet (backend answers 501); the URL is exposed for phase 7. */
  tileUrl: (id: string, z: number, x: number, y: number) =>
    `${API_URL}/changes/${id}/tiles/${z}/${x}/${y}`,
};
