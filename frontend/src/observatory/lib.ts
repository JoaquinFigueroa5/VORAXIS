import type { MultiPolygon, Polygon } from "geojson";

import { API_URL } from "@/services/api";

/** Scheme + host of the API: tile paths from the backend already carry /api/v1. */
export const API_ORIGIN = new URL(API_URL).origin;

export interface ChangeTypeStyle {
  label: string;
  color: string;
  /** One plain sentence on why the radar suggests this. */
  reading: string;
}

export const CHANGE_TYPES: Record<string, ChangeTypeStyle> = {
  POSSIBLE_FLOODING: {
    label: "Posible inundación",
    color: "#1f6fb2",
    reading:
      "La superficie se oscureció para el radar. El agua en calma refleja la señal lejos del satélite, así que el terreno anegado se ve más oscuro.",
  },
  POSSIBLE_FLOODED_VEGETATION: {
    label: "Posible vegetación inundada",
    color: "#2a9d8f",
    reading:
      "La superficie se aclaró tras lluvia anómala. Agua bajo vegetación hace rebotar la señal dos veces (agua y tallos) y la devuelve con más fuerza.",
  },
  POSSIBLE_BURN_SCAR: {
    label: "Posible área quemada",
    color: "#c2410c",
    reading:
      "Hay focos de fuego activo junto al área en el intervalo. Al quemarse la vegetación, la señal de radar suele bajar.",
  },
  POSSIBLE_VEGETATION_LOSS: {
    label: "Posible pérdida de vegetación",
    color: "#8d6e3f",
    reading:
      "La señal bajó desde un nivel propio de vegetación densa, sin fuego cercano ni firma de agua. Es compatible con tala o cosecha.",
  },
  POSSIBLE_WATER_RECESSION: {
    label: "Posible retroceso de agua",
    color: "#7c8fa6",
    reading:
      "Una superficie que tenía firma de agua en la primera fecha dejó de tenerla en la segunda.",
  },
  POSSIBLE_SEISMIC_DISTURBANCE: {
    label: "Posible alteración por sismo",
    color: "#b0305c",
    reading:
      "Hubo un sismo fuerte cerca en el intervalo. Esta medida no mide desplazamiento del terreno; es solo una coincidencia a revisar.",
  },
  UNCLASSIFIED: {
    label: "Cambio sin clasificar",
    color: "#7a7a7a",
    reading:
      "La señal cambió, pero ni su firma ni los eventos cercanos permiten proponer una causa.",
  },
};

export function typeStyle(changeType: string): ChangeTypeStyle {
  return CHANGE_TYPES[changeType] ?? { ...CHANGE_TYPES.UNCLASSIFIED, label: changeType };
}

const DAY = new Intl.DateTimeFormat("es", { day: "numeric", month: "short", timeZone: "UTC" });
const DAY_YEAR = new Intl.DateTimeFormat("es", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export function shortDate(value: string | null | undefined, withYear = false): string {
  if (!value) return "sin fecha";
  return (withYear ? DAY_YEAR : DAY).format(new Date(value)).replace(".", "");
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
  if (value === null || value === undefined) return "sin dato";
  return value.toLocaleString("es", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function area(km2: number | null | undefined): string {
  if (km2 === null || km2 === undefined) return "sin dato";
  if (km2 < 1) return `${number(km2 * 100, km2 < 0.1 ? 1 : 0)} ha`;
  return `${number(km2, km2 < 10 ? 2 : 1)} km²`;
}

export function signedDb(value: number | null | undefined): string {
  if (value === null || value === undefined) return "sin dato";
  return `${value > 0 ? "+" : "−"}${number(Math.abs(value), 1)} dB`;
}

export function db(value: number | null | undefined): string {
  if (value === null || value === undefined) return "sin dato";
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
