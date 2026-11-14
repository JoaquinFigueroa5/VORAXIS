import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("es", { dateStyle: "medium" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("es", { dateStyle: "medium", timeStyle: "short" });
}

export function formatArea(km2: number | null | undefined): string {
  if (km2 === null || km2 === undefined) return "—";
  if (km2 < 0.01) return `${(km2 * 1_000_000).toFixed(0)} m²`;
  if (km2 < 1) return `${(km2 * 100).toFixed(2)} ha`;
  return `${km2.toFixed(2)} km²`;
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(digits)} %`;
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("es", { maximumFractionDigits: digits });
}
