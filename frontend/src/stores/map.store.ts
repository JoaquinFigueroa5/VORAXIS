import { create } from "zustand";

interface Layers {
  aoi: boolean;
  scenes: boolean;
  changes: boolean;
  auxiliary: boolean;
}

interface MapState {
  center: [number, number];
  zoom: number;
  selectedLocationId: string | null;
  layers: Layers;
  setView: (center: [number, number], zoom?: number) => void;
  selectLocation: (id: string | null) => void;
  toggleLayer: (layer: keyof Layers) => void;
}

export const useMapStore = create<MapState>((set) => ({
  center: [-90.2, 16.8],
  zoom: 7,
  selectedLocationId: null,
  layers: { aoi: true, scenes: true, changes: true, auxiliary: true },
  setView: (center, zoom) => set((state) => ({ center, zoom: zoom ?? state.zoom })),
  selectLocation: (selectedLocationId) => set({ selectedLocationId }),
  toggleLayer: (layer) =>
    set((state) => ({ layers: { ...state.layers, [layer]: !state.layers[layer] } })),
}));
