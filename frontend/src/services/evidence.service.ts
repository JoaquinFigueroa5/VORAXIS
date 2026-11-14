import { apiFetch, buildQuery } from "@/services/api";
import type { AuxiliaryEvent, EvidenceRecord } from "@/types/evidence";

export const evidenceService = {
  forChange: (changeId: string) =>
    apiFetch<EvidenceRecord[]>(`/changes/${changeId}/evidence`),
  listAuxiliary: (params: { source?: string; event_type?: string; bbox?: string } = {}) =>
    apiFetch<AuxiliaryEvent[]>(`/auxiliary/events${buildQuery(params)}`),
};
