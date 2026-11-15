import { apiFetch, buildQuery } from "@/services/api";
import type { Location, LocationCreate } from "@/types/location";

export const locationsService = {
  list: (limit = 100) => apiFetch<Location[]>(`/locations${buildQuery({ limit })}`),
  search: (query: string) =>
    apiFetch<Location[]>(`/locations/search${buildQuery({ q: query })}`),
  get: (id: string) => apiFetch<Location>(`/locations/${id}`),
  /** 409 when the name is taken, 400 with the reason when the area is invalid. */
  create: (location: LocationCreate) =>
    apiFetch<Location>("/locations", { method: "POST", body: JSON.stringify(location) }),
};
