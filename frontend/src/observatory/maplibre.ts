/**
 * MapLibre 6 ships its worker as a separate ES module. Vite pre-bundles the
 * library, which breaks the worker's relative URL, so the URL is given
 * explicitly. Import map classes from here, never from "maplibre-gl" directly.
 */
import { setWorkerUrl } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import "maplibre-gl/dist/maplibre-gl.css";

setWorkerUrl(workerUrl);

// Basemaps live in observatory/basemap.tsx.

export * from "maplibre-gl";
