import { apiFetch } from "@/services/api";
import type { InsightsSummary, JobInsights } from "@/types/analysis";

export const insightsService = {
  summary: () => apiFetch<InsightsSummary>("/insights"),
  /** By change type and direction, histograms, linked evidence and the rain series. */
  forJob: (jobId: string) => apiFetch<JobInsights>(`/jobs/${jobId}/insights`),
};
