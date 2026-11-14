import { useQuery } from "@tanstack/react-query";

import { locationsService } from "@/services/locations.service";

export function useLocations(limit = 100) {
  return useQuery({
    queryKey: ["locations", limit],
    queryFn: () => locationsService.list(limit),
  });
}

export function useLocationSearch(query: string) {
  return useQuery({
    queryKey: ["locations", "search", query],
    queryFn: () => locationsService.search(query),
    enabled: query.trim().length > 1,
  });
}
