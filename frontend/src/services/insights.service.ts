import { apiFetch } from "@/services/api";
import type { InsightsSummary } from "@/types/analysis";

export const insightsService = {
  summary: () => apiFetch<InsightsSummary>("/insights"),
};
