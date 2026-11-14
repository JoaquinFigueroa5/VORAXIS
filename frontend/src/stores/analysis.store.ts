import { create } from "zustand";

interface AnalysisState {
  beforeObservationId: string | null;
  afterObservationId: string | null;
  selectedChangeId: string | null;
  setBefore: (id: string | null) => void;
  setAfter: (id: string | null) => void;
  selectChange: (id: string | null) => void;
  reset: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  beforeObservationId: null,
  afterObservationId: null,
  selectedChangeId: null,
  setBefore: (beforeObservationId) => set({ beforeObservationId }),
  setAfter: (afterObservationId) => set({ afterObservationId }),
  selectChange: (selectedChangeId) => set({ selectedChangeId }),
  reset: () =>
    set({ beforeObservationId: null, afterObservationId: null, selectedChangeId: null }),
}));
