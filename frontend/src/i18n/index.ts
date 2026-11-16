import { useLocale, type Locale } from "@/stores/locale";
import { en } from "./en";
import { es } from "./es";

/** What the backend sends instead of prose: a stable code and the values to fill in. */
export interface Coded {
  code: string;
  params?: Record<string, unknown> | null;
}

export type MessageKey = keyof typeof es;

const DICTIONARIES: Record<Locale, Record<string, string>> = { es, en };

/** The language the interface is being written in right now. */
export function currentLocale(): Locale {
  return useLocale.getState().locale;
}

/** For `Intl` and `toLocaleString`. */
export function intlLocale(): string {
  return currentLocale() === "en" ? "en-US" : "es";
}

function fill(template: string, params?: Record<string, unknown> | null): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    params[name] === undefined || params[name] === null ? match : String(params[name]),
  );
}

/**
 * The text for `key` in the current language, or `fallback` (the key itself if
 * none) when the dictionary lacks it. Outside components it reads the language
 * at call time; components call `useT()` so they re-render when it changes.
 */
export function t(key: string, params?: Record<string, unknown> | null, fallback?: string): string {
  const template = DICTIONARIES[currentLocale()][key];
  return template === undefined ? (fallback ?? key) : fill(template, params);
}

/** `t` for components: subscribes to the language, so switching it re-renders. */
export function useT(): typeof t {
  useLocale((state) => state.locale);
  return t;
}

export function has(key: string): boolean {
  return key in DICTIONARIES[currentLocale()];
}

/** A source code (FIRMS, USGS...) as people read it. */
export function sourceName(source: unknown): string {
  const name = String(source ?? "");
  return t(`source.${name.toUpperCase()}`, null, name);
}

/** `{code, params}` under a dictionary section, e.g. `coded("reason", reason)`. */
export function coded(section: string, message: Coded, fallback?: string): string {
  const params = { ...(message.params ?? {}) };
  if ("source" in params) params.source = sourceName(params.source);
  return t(`${section}.${message.code}`, params, fallback);
}

// Screen readers and hyphenation follow <html lang>; the tab title follows the language too.
function syncDocument(locale: Locale) {
  document.documentElement.lang = locale;
  document.title = DICTIONARIES[locale]["app.title"] ?? document.title;
}

if (typeof document !== "undefined") {
  syncDocument(currentLocale());
  useLocale.subscribe((state) => syncDocument(state.locale));
}
