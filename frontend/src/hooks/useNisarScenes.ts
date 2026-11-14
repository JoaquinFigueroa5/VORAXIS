import { useQuery } from "@tanstack/react-query";

import { nisarService } from "@/services/nisar.service";
import type { SceneFilters } from "@/types/nisar";

export function useNisarScenes(filters: SceneFilters) {
  return useQuery({
    queryKey: ["nisar", "scenes", filters],
    queryFn: () => nisarService.listScenes(filters),
  });
}
