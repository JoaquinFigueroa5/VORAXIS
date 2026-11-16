import type { MultiPolygon, Polygon } from "geojson";

import { intlLocale, t } from "@/i18n";
import { API_URL } from "@/services/api";

/** Scheme + host of the API: tile paths from the backend already carry /api/v1. */
export const API_ORIGIN = new URL(API_URL).origin;

export interface ChangeTypeStyle {
  label: string;
  color: string;
  /** One plain sentence on why the radar suggests this. */
  reading: string;
}

/** Colours are fixed; the words come from the dictionaries (`changeType.<type>.label`). */
export const TYPE_COLORS: Record<string, string> = {
  POSSIBLE_FLOODING: "#1f6fb2",
  POSSIBLE_FLOODED_VEGETATION: "#2a9d8f",
  POSSIBLE_BURN_SCAR: "#c2410c",
  POSSIBLE_VEGETATION_LOSS: "#8d6e3f",
  POSSIBLE_WATER_RECESSION: "#7c8fa6",
  POSSIBLE_SEISMIC_DISTURBANCE: "#b0305c",
  UNCLASSIFIED: "#7a7a7a",
};

export function typeStyle(changeType: string): ChangeTypeStyle {
  const known = changeType in TYPE_COLORS;
  const type = known ? changeType : "UNCLASSIFIED";
  return {
    label: known ? t(`changeType.${type}.label`) : changeType,
    color: TYPE_COLORS[type],
    reading: t(`changeType.${type}.reading`),
  };
}

const formats = new Map<string, Intl.DateTimeFormat>();

function dateFormat(withYear: boolean): Intl.DateTimeFormat {
  const locale = intlLocale();
  const key = `${locale}:${withYear}`;
  let format = formats.get(key);
  if (!format) {
    format = new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "short",
      ...(withYear ? { year: "numeric" } : {}),
      timeZone: "UTC",
    });
    formats.set(key, format);
  }
  return format;
}

export function shortDate(value: string | null | undefined, withYear = false): string {
  if (!value) return t("value.no_date");
  return dateFormat(withYear).format(new Date(value)).replace(".", "");
}

export function isoDay(value: string): string {
  return value.slice(0, 10);
}

export function addDays(day: string, amount: number): string {
  const date = new Date(`${day}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

export function number(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return t("value.no_data");
  return value.toLocaleString(intlLocale(), { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function area(km2: number | null | undefined): string {
  if (km2 === null || km2 === undefined) return t("value.no_data");
  if (km2 < 1) return `${number(km2 * 100, km2 < 0.1 ? 1 : 0)} ha`;
  return `${number(km2, km2 < 10 ? 2 : 1)} km²`;
}

export function signedDb(value: number | null | undefined): string {
  if (value === null || value === undefined) return t("value.no_data");
  return `${value > 0 ? "+" : "−"}${number(Math.abs(value), 1)} dB`;
}

export function db(value: number | null | undefined): string {
  if (value === null || value === undefined) return t("value.no_data");
  return `${value < 0 ? "−" : ""}${number(Math.abs(value), 1)} dB`;
}

export type Bounds = [number, number, number, number];

export function geometryBounds(geometry: Polygon | MultiPolygon): Bounds {
  let west = 180;
  let south = 90;
  let east = -180;
  let north = -90;
  const rings = geometry.type === "Polygon" ? geometry.coordinates : geometry.coordinates.flat();
  for (const ring of rings) {
    for (const [lon, lat] of ring) {
      if (lon < west) west = lon;
      if (lon > east) east = lon;
      if (lat < south) south = lat;
      if (lat > north) north = lat;
    }
  }
  return [west, south, east, north];
}

export function boundsCenter([west, south, east, north]: Bounds): { lon: number; lat: number } {
  return { lon: (west + east) / 2, lat: (south + north) / 2 };
}
