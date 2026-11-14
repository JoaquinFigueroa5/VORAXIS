import { useQuery } from "@tanstack/react-query";

import { changesService } from "@/services/changes.service";

export function useChanges(jobId: string | undefined) {
  return useQuery({
    queryKey: ["changes", { job_id: jobId }],
    queryFn: () => changesService.list({ job_id: jobId }),
    enabled: Boolean(jobId),
  });
}

export function useChange(changeId: string | undefined) {
  return useQuery({
    queryKey: ["change", changeId],
    queryFn: () => changesService.get(changeId as string),
    enabled: Boolean(changeId),
  });
}

export function useChangeMetrics(changeId: string | undefined) {
  return useQuery({
    queryKey: ["changes", changeId, "metrics"],
    queryFn: () => changesService.metrics(changeId as string),
    enabled: Boolean(changeId),
  });
}
