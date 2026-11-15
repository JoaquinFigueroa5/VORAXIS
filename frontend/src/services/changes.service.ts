import { API_URL, ApiError, apiFetch } from "@/services/api";
import type {
  ChangeCollection,
  ChangeEvent,
  ChangeFilters,
  ChangeMetric,
  ChangePage,
  TileDescription,
  TileLayer,
} from "@/types/change";

/** `change_type` repeats in the query string, which URLSearchParams.set cannot express. */
function query(params: Record<string, string | number | string[] | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
    else search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const changesService = {
  list: (params: ChangeFilters & { limit?: number; offset?: number } = {}) =>
    apiFetch<ChangeEvent[]>(`/changes${query({ ...params, limit: params.limit ?? 100 })}`),
  /** One page plus the total that matches the filters (limit up to 1000). */
  page: async (params: ChangeFilters & { limit?: number; offset?: number } = {}): Promise<ChangePage> => {
    const response = await fetch(`${API_URL}/changes${query({ ...params, limit: params.limit ?? 100 })}`);
    if (!response.ok) throw new ApiError(response.status, response.statusText);
    return {
      items: (await response.json()) as ChangeEvent[],
      total: Number(response.headers.get("X-Total-Count") ?? 0),
    };
  },
  /**
   * Changes as a map layer. Pass the current map `zoom` to get geometry
   * simplified to one pixel; properties carry type, label, direction and score.
   */
  geojson: (params: ChangeFilters & { zoom?: number; limit?: number } = {}) =>
    apiFetch<ChangeCollection>(`/changes/geojson${query(params)}`),
  /** Vector tiles (layer "changes") for a MapLibre `vector` source: fastest for thousands of polygons. */
  vectorTileTemplate: (jobId: string) => `${API_URL}/jobs/${jobId}/changes/tiles/{z}/{x}/{y}.mvt`,
  get: (id: string) => apiFetch<ChangeEvent>(`/changes/${id}`),
  metrics: (id: string) => apiFetch<ChangeMetric[]>(`/changes/${id}/metrics`),
  /** Layer URLs, bounds, zoom range and legend for the map. */
  tiles: (id: string) => apiFetch<TileDescription>(`/changes/${id}/tiles`),
  /** XYZ template for a MapLibre raster source: pass it straight to `tiles: [url]`. */
  tileTemplate: (id: string, layer: TileLayer = "difference") =>
    `${API_URL}/changes/${id}/tiles/{z}/{x}/{y}?layer=${layer}`,
};
