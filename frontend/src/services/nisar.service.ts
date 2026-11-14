import { apiFetch, buildQuery } from "@/services/api";
import type { NisarScene, SceneFilters } from "@/types/nisar";

export const nisarService = {
  listScenes: (filters: SceneFilters = {}) =>
    apiFetch<NisarScene[]>(
      `/nisar/scenes${buildQuery({ ...filters, limit: filters.limit ?? 100 })}`,
    ),
  getScene: (id: string) => apiFetch<NisarScene>(`/nisar/scenes/${id}`),
};
