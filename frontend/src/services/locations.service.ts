import { apiFetch, buildQuery } from "@/services/api";
import type { Location } from "@/types/location";

export const locationsService = {
  list: (limit = 100) => apiFetch<Location[]>(`/locations${buildQuery({ limit })}`),
  search: (query: string) =>
    apiFetch<Location[]>(`/locations/search${buildQuery({ q: query })}`),
  get: (id: string) => apiFetch<Location>(`/locations/${id}`),
};
