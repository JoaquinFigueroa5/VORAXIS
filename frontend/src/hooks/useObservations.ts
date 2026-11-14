import { useQuery } from "@tanstack/react-query";

import { observationsService } from "@/services/observations.service";

export function useObservations(params: { location_id?: string } = {}) {
  return useQuery({
    queryKey: ["observations", params],
    queryFn: () => observationsService.list(params),
  });
}
