import { apiFetch } from "@/services/api";
import type { Interpretation } from "@/types/interpretation";

export const interpretationService = {
  /** Metrics, linked evidence, source status and the reasons behind the label. */
  forChange: (changeId: string) => apiFetch<Interpretation>(`/changes/${changeId}/interpretation`),
};
