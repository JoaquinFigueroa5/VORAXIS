import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Locale = "es" | "en";

function detect(): Locale {
  return navigator.language.toLowerCase().startsWith("en") ? "en" : "es";
}

/** Spanish is the default; the choice is remembered and never goes in the URL. */
interface LocaleState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

export const useLocale = create<LocaleState>()(
  persist(
    (set) => ({
      locale: detect(),
      setLocale: (locale) => set({ locale }),
    }),
    { name: "voraxis.locale" },
  ),
);
