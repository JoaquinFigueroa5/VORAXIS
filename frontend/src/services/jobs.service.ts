import { apiFetch, buildQuery } from "@/services/api";
import type { ProcessingJob } from "@/types/job";

export const jobsService = {
  get: (id: string) => apiFetch<ProcessingJob>(`/jobs/${id}`),
  list: (params: { status?: string; limit?: number } = {}) =>
    apiFetch<ProcessingJob[]>(`/jobs${buildQuery(params)}`),
  cancel: (id: string) => apiFetch<ProcessingJob>(`/jobs/${id}/cancel`, { method: "POST" }),
};
