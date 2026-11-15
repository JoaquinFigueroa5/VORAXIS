import { API_URL, apiFetch, buildQuery } from "@/services/api";
import type { ChangeEvent, ChangeMetric, TileDescription, TileLayer } from "@/types/change";

export const changesService = {
  list: (params: { job_id?: string; bbox?: string; limit?: number } = {}) =>
    apiFetch<ChangeEvent[]>(`/changes${buildQuery({ ...params, limit: params.limit ?? 100 })}`),
  get: (id: string) => apiFetch<ChangeEvent>(`/changes/${id}`),
  metrics: (id: string) => apiFetch<ChangeMetric[]>(`/changes/${id}/metrics`),
  /** Layer URLs, bounds, zoom range and legend for the map. */
  tiles: (id: string) => apiFetch<TileDescription>(`/changes/${id}/tiles`),
  /** XYZ template for a MapLibre raster source: pass it straight to `tiles: [url]`. */
  tileTemplate: (id: string, layer: TileLayer = "difference") =>
    `${API_URL}/changes/${id}/tiles/{z}/{x}/{y}?layer=${layer}`,
};
