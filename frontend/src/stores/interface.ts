import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Explore mode hides the numbers; scientific mode shows dB, thresholds and the
 * processing metadata. Same screens, two levels of detail.
 */
interface InterfaceState {
  scientific: boolean;
  toggleScientific: () => void;
}

export const useInterface = create<InterfaceState>()(
  persist(
    (set) => ({
      scientific: false,
      toggleScientific: () => set((state) => ({ scientific: !state.scientific })),
    }),
    { name: "voraxis.interface" },
  ),
);
