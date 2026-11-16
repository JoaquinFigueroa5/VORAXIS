/**
 * Basemaps the user can pick under any map. Grey stays the default: the change
 * layers speak in red and blue, and a coloured map has blue water and green land
 * of its own. The colour maps help to recognise the ground (town, crop, forest).
 */
import { useSyncExternalStore } from "react";

import { t, useT } from "@/i18n";
import type { Map as MapLibreMap, RasterSourceSpecification } from "@/observatory/maplibre";

export type BasemapId = "gris" | "satelite" | "nasa";

interface Basemap {
  label: string;
  tiles: string;
  labels: string;
  /** Deepest zoom the provider serves; MapLibre stretches the last level beyond it. */
  maxzoom: number;
  attribution: string;
  /** Colour for lines drawn over the map (zones, radius, footprints). */
  ink: string;
}

const ESRI = "https://services.arcgisonline.com/ArcGIS/rest/services";
const PLACES = `${ESRI}/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}`;

export const BASEMAPS: Record<BasemapId, Basemap> = {
  gris: {
    label: "basemap.gris",
    tiles: `${ESRI}/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`,
    labels: `${ESRI}/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}`,
    maxzoom: 15,
    attribution: "basemap.credit.gris",
    ink: "#232323",
  },
  satelite: {
    label: "basemap.satelite",
    tiles: `${ESRI}/World_Imagery/MapServer/tile/{z}/{y}/{x}`,
    labels: PLACES,
    maxzoom: 17,
    attribution: "basemap.credit.satelite",
    ink: "#ffffff",
  },
  nasa: {
    label: "basemap.nasa",
    // The same Blue Marble that Earthdata Search and Worldview open with (GIBS, no key).
    tiles:
      "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg",
    labels: PLACES,
    maxzoom: 8,
    attribution: "basemap.credit.nasa",
    ink: "#ffffff",
  },
};

const ORDER: BasemapId[] = ["gris", "satelite", "nasa"];

/** The two raster sources a map style needs, named "base" and "labels". */
export function basemapSources(id: BasemapId, extraAttribution = ""): Record<"base" | "labels", RasterSourceSpecification> {
  const map = BASEMAPS[id];
  return {
    base: {
      type: "raster",
      tiles: [map.tiles],
      tileSize: 256,
      maxzoom: map.maxzoom,
      attribution: extraAttribution ? `${t(map.attribution)} | ${extraAttribution}` : t(map.attribution),
    },
    // Labels come from Esri at full detail whatever the imagery underneath.
    labels: { type: "raster", tiles: [map.labels], tileSize: 256, maxzoom: 15 },
  };
}

/** Swap the "base" and "labels" sources of a live map, keeping every other layer and its order. */
export function applyBasemap(map: MapLibreMap, id: BasemapId, extraAttribution = "") {
  const sources = basemapSources(id, extraAttribution);
  for (const name of ["base", "labels"] as const) {
    if (!map.getSource(name)) continue;
    const layers = map.getStyle().layers;
    const index = layers.findIndex((layer) => layer.id === name);
    const above = layers[index + 1]?.id;
    map.removeLayer(name);
    map.removeSource(name);
    map.addSource(name, sources[name]);
    map.addLayer({ id: name, type: "raster", source: name }, above);
  }
}

// ---- the choice, shared by every map and kept between visits

const KEY = "voraxis.basemap";
const listeners = new Set<() => void>();
let current: BasemapId = read();

function read(): BasemapId {
  try {
    const stored = localStorage.getItem(KEY);
    return stored && stored in BASEMAPS ? (stored as BasemapId) : "gris";
  } catch {
    return "gris";
  }
}

export function setBasemap(id: BasemapId) {
  current = id;
  try {
    localStorage.setItem(KEY, id);
  } catch {
    // Private window: the choice lasts until reload.
  }
  listeners.forEach((listener) => listener());
}

export function useBasemap(): BasemapId {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => current,
  );
}

/** Three options over the map, bottom right above the credits. */
export function BasemapSwitch() {
  const value = useBasemap();
  const t = useT();
  return (
    <div className="basemap" role="group" aria-label={t("basemap.aria")}>
      {ORDER.map((id) => (
        <button key={id} type="button" aria-pressed={value === id} onClick={() => setBasemap(id)}>
          {t(BASEMAPS[id].label)}
        </button>
      ))}
    </div>
  );
}
