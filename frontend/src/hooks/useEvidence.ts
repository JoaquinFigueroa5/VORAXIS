import { useQuery } from "@tanstack/react-query";

import { evidenceService } from "@/services/evidence.service";

export function useEvidence(changeId: string | undefined) {
  return useQuery({
    queryKey: ["evidence", changeId],
    queryFn: () => evidenceService.forChange(changeId as string),
    enabled: Boolean(changeId),
  });
}

export function useAuxiliaryEvents(params: { source?: string; event_type?: string } = {}) {
  return useQuery({
    queryKey: ["auxiliary", params],
    queryFn: () => evidenceService.listAuxiliary(params),
  });
}
