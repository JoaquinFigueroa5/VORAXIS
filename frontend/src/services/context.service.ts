import { apiFetch, buildQuery } from "@/services/api";
import type {
  ContextQuery,
  EarthquakeContext,
  FireContext,
  NisarContext,
  PrecipitationContext,
  TimelineContext,
} from "@/types/context";

/**
 * Live lookups for any point on the map. They hit the public catalogues
 * (ASF, USGS, NASA POWER, NASA FIRMS) and are cached server-side for a few
 * minutes; a failing source answers 502 with the reason in `detail`.
 */
export const contextService = {
  /** NISAR products over the point, freshness per level and analysable GCOV pairs. */
  nisar: (params: ContextQuery & { level?: string; max_results?: number }) =>
    apiFetch<NisarContext>(`/context/nisar${buildQuery(params)}`),
  earthquakes: (params: ContextQuery & { radius_km?: number; min_magnitude?: number }) =>
    apiFetch<EarthquakeContext>(`/context/earthquakes${buildQuery(params)}`),
  precipitation: (params: ContextQuery) =>
    apiFetch<PrecipitationContext>(`/context/precipitation${buildQuery(params)}`),
  /** At most 31 days per request. */
  fires: (params: ContextQuery & { radius_km?: number }) =>
    apiFetch<FireContext>(`/context/fires${buildQuery(params)}`),
  /** Acquisitions, earthquakes, heavy-rain days and fire days, newest first. */
  timeline: (params: ContextQuery & { radius_km?: number; min_magnitude?: number }) =>
    apiFetch<TimelineContext>(`/context/timeline${buildQuery(params)}`),
};
