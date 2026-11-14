import { create } from "zustand";
import { daysAgoISO, todayISO } from "@/utils/dates";

interface FiltersState {
  startDate: string;
  endDate: string;
  productType: string;
  maturity: string;
  setRange: (startDate: string, endDate: string) => void;
  setProductType: (productType: string) => void;
  setMaturity: (maturity: string) => void;
  reset: () => void;
}

const initial = {
  startDate: daysAgoISO(60),
  endDate: todayISO(),
  productType: "",
  maturity: "",
};

export const useFiltersStore = create<FiltersState>((set) => ({
  ...initial,
  setRange: (startDate, endDate) => set({ startDate, endDate }),
  setProductType: (productType) => set({ productType }),
  setMaturity: (maturity) => set({ maturity }),
  reset: () => set(initial),
}));
