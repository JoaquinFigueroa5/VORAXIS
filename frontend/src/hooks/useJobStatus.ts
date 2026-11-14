import { useQuery } from "@tanstack/react-query";

import { jobsService } from "@/services/jobs.service";
import { FINAL_JOB_STATUSES } from "@/types/job";

export function useJobStatus(jobId: string | undefined) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => jobsService.get(jobId as string),
    enabled: Boolean(jobId),
    // Poll only while the job can still change state.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && !FINAL_JOB_STATUSES.includes(status) ? 2000 : false;
    },
  });
}
