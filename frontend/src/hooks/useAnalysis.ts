import { useMutation } from "@tanstack/react-query";

import { analysisService } from "@/services/analysis.service";
import type { AnalysisRequest } from "@/types/analysis";

export function useAnalysis() {
  return useMutation({
    mutationFn: (payload: AnalysisRequest) => analysisService.create(payload),
  });
}
