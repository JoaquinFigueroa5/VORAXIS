import { apiFetch, buildQuery } from "@/services/api";
import type { Observation } from "@/types/observation";

export const observationsService = {
  list: (params: { location_id?: string; scene_id?: string; limit?: number } = {}) =>
    apiFetch<Observation[]>(`/observations${buildQuery({ ...params, limit: params.limit ?? 100 })}`),
  get: (id: string) => apiFetch<Observation>(`/observations/${id}`),
};
