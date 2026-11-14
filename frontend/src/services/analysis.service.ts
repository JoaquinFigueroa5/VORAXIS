import { apiFetch } from "@/services/api";
import type { AnalysisAccepted, AnalysisRequest } from "@/types/analysis";

export const analysisService = {
  create: (payload: AnalysisRequest) =>
    apiFetch<AnalysisAccepted>("/analysis", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
