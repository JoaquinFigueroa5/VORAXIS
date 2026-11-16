import type { Locale } from "@/stores/locale";
import { en } from "./en";
import { es } from "./es";

/** What the backend sends instead of prose: a stable code and the values to fill in. */
export interface Coded {
  code: string;
  params?: Record<string, unknown> | null;
}

const DICTIONARIES: Record<Locale, Record<string, string>> = { es, en };

/**
 * The pages are still written in Spanish, so backend codes are written in Spanish too.
 * Switch this to `useLocale` once every page reads its copy through `t()`.
 */
const UI_LOCALE: Locale = "es";

function fill(template: string, params?: Record<string, unknown> | null): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    params[name] === undefined || params[name] === null ? match : String(params[name]),
  );
}

/** The text for `key`, or `fallback` (the key itself if none) when the dictionary lacks it. */
export function t(key: string, params?: Record<string, unknown> | null, fallback?: string): string {
  const template = DICTIONARIES[UI_LOCALE][key];
  return template === undefined ? (fallback ?? key) : fill(template, params);
}

export function has(key: string): boolean {
  return key in DICTIONARIES[UI_LOCALE];
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
