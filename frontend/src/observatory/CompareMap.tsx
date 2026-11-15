import {
  Map as MapLibreMap,
  NavigationControl,
  type ExpressionSpecification,
  type FilterSpecification,
  type MapMouseEvent,
  type StyleSpecification,
} from "@/observatory/maplibre";
import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";

import { BasemapSwitch, applyBasemap, basemapSources, useBasemap, type BasemapId } from "@/observatory/basemap";
import { API_ORIGIN, CHANGE_TYPES, type Bounds } from "@/observatory/lib";
import { changesService } from "@/services/changes.service";
import type { TileDescription } from "@/types/change";

export type ViewMode = "comparar" | "cambio" | "antes" | "despues";

interface CompareMapProps {
  jobId: string;
  tiles: TileDescription;
  mode: ViewMode;
  showPolygons: boolean;
  hiddenTypes: string[];
  selectedId: string | null;
  onSelect: (changeId: string | null) => void;
  /** Bounds to fly to (a change picked from the list). */
  focus: Bounds | null;
  beforeLabel: string;
  afterLabel: string;
  /** Inside the landing hero: no zoom buttons, no wheel or drag, only the swipe. */
  bare?: boolean;
}

const RADAR_CREDIT = "Radar: NISAR (NASA/ISRO), ASF DAAC";

const TYPE_COLOR: ExpressionSpecification = [
  "match",
  ["get", "change_type"],
  ...Object.entries(CHANGE_TYPES).flatMap(([type, style]) => [type, style.color]),
  CHANGE_TYPES.UNCLASSIFIED.color,
] as unknown as ExpressionSpecification;

function style(jobId: string, tiles: TileDescription, radar: "before" | "after", basemap: BasemapId): StyleSpecification {
  const raster = (layer: "before" | "after" | "difference") => ({
    type: "raster" as const,
    tiles: [`${API_ORIGIN}${tiles.layers[layer] ?? ""}`],
    tileSize: 256,
    maxzoom: tiles.maxzoom,
    ...(tiles.bounds ? { bounds: tiles.bounds } : {}),
  });
  return {
    version: 8,
    sources: {
      ...basemapSources(basemap, RADAR_CREDIT),
      radar: raster(radar),
      difference: raster("difference"),
      changes: {
        type: "vector",
        tiles: [changesService.vectorTileTemplate(jobId)],
        maxzoom: 13,
        ...(tiles.bounds ? { bounds: tiles.bounds } : {}),
      },
    },
    layers: [
      { id: "base", type: "raster", source: "base" },
      { id: "radar", type: "raster", source: "radar", paint: { "raster-fade-duration": 0 } },
      {
        id: "difference",
        type: "raster",
        source: "difference",
        layout: { visibility: "none" },
        paint: { "raster-fade-duration": 0 },
      },
      {
        id: "changes-fill",
        type: "fill",
        source: "changes",
        "source-layer": "changes",
        paint: { "fill-color": TYPE_COLOR, "fill-opacity": 0.3 },
      },
      {
        id: "changes-line",
        type: "line",
        source: "changes",
        "source-layer": "changes",
        paint: { "line-color": TYPE_COLOR, "line-width": 1 },
      },
      {
        id: "selected-casing",
        type: "line",
        source: "changes",
        "source-layer": "changes",
        filter: ["==", ["get", "id"], ""],
        paint: { "line-color": "#232323", "line-width": 6 },
      },
      {
        id: "selected",
        type: "line",
        source: "changes",
        "source-layer": "changes",
        filter: ["==", ["get", "id"], ""],
        paint: { "line-color": "#a1ffcb", "line-width": 3 },
      },
      { id: "labels", type: "raster", source: "labels" },
    ],
  };
}

const POLYGON_LAYERS = ["changes-fill", "changes-line"];

/**
 * Two synchronised maps: "after" below, "before" above and clipped at the swipe
 * handle. Polygons live on both so they stay visible on either side.
 */
export function CompareMap({
  jobId,
  tiles,
  mode,
  showPolygons,
  hiddenTypes,
  selectedId,
  onSelect,
  focus,
  beforeLabel,
  afterLabel,
  bare = false,
}: CompareMapProps) {
  const afterRef = useRef<HTMLDivElement | null>(null);
  const beforeRef = useRef<HTMLDivElement | null>(null);
  const frameRef = useRef<HTMLDivElement | null>(null);
  const maps = useRef<{ after: MapLibreMap; before: MapLibreMap } | null>(null);
  const select = useRef(onSelect);
  select.current = onSelect;
  const [ready, setReady] = useState(false);
  const [position, setPosition] = useState(50);
  // The landing hero keeps the grey map; everywhere else the user's choice.
  const chosen = useBasemap();
  const basemap: BasemapId = bare ? "gris" : chosen;
  const initialBasemap = useRef(basemap);
  initialBasemap.current = basemap;
  const shownBasemap = useRef(basemap);

  // Build both maps once per analysis.
  useEffect(() => {
    if (!afterRef.current || !beforeRef.current) return;
    const built = initialBasemap.current;
    const options = {
      attributionControl: false as const,
      interactive: !bare,
      maxZoom: Math.max(tiles.maxzoom + 2, 14),
      ...(tiles.bounds
        ? { bounds: tiles.bounds, fitBoundsOptions: { padding: 30 } }
        : { center: [0, 15] as [number, number], zoom: 2 }),
    };
    // Credits are shown once, on the lower map.
    const after = new MapLibreMap({
      container: afterRef.current,
      style: style(jobId, tiles, "after", built),
      ...options,
      // In the hero the page footer carries the credits.
      attributionControl: bare ? false : { compact: true },
    });
    const before = new MapLibreMap({ container: beforeRef.current, style: style(jobId, tiles, "before", built), ...options });
    if (!bare) after.addControl(new NavigationControl({ showCompass: false }), "top-right");

    let syncing = false;
    const follow = (leader: MapLibreMap, follower: MapLibreMap) => () => {
      if (syncing) return;
      syncing = true;
      follower.jumpTo({ center: leader.getCenter(), zoom: leader.getZoom(), bearing: leader.getBearing(), pitch: leader.getPitch() });
      syncing = false;
    };
    after.on("move", follow(after, before));
    before.on("move", follow(before, after));

    for (const map of [after, before]) {
      map.on("click", (event: MapMouseEvent) => {
        const [feature] = map.queryRenderedFeatures(event.point, { layers: ["changes-fill"] });
        select.current(feature ? String(feature.properties.id) : null);
      });
      map.on("mousemove", (event: MapMouseEvent) => {
        const hit = map.getLayer("changes-fill")
          ? map.queryRenderedFeatures(event.point, { layers: ["changes-fill"] }).length > 0
          : false;
        map.getCanvas().style.cursor = hit ? "pointer" : "";
      });
    }

    let loaded = 0;
    const onLoad = () => {
      loaded += 1;
      if (loaded === 2) {
        // In the hero the radar should fill the window, not sit inside a margin of basemap.
        if (bare) after.jumpTo({ zoom: after.getZoom() + 0.8 });
        maps.current = { after, before };
        shownBasemap.current = built;
        setReady(true);
      }
    };
    after.once("load", onLoad);
    before.once("load", onLoad);

    return () => {
      maps.current = null;
      setReady(false);
      after.remove();
      before.remove();
    };
  }, [jobId, tiles, bare]);

  // Mode, polygon visibility, type filter and selection are plain style updates.
  useEffect(() => {
    const pair = maps.current;
    if (!ready || !pair) return;
    pair.after.setLayoutProperty("difference", "visibility", mode === "cambio" ? "visible" : "none");
    const visible: FilterSpecification = ["!", ["in", ["get", "change_type"], ["literal", hiddenTypes]]];
    const chosen: FilterSpecification = ["==", ["get", "id"], selectedId ?? ""];
    for (const map of [pair.after, pair.before]) {
      for (const layer of POLYGON_LAYERS) {
        map.setLayoutProperty(layer, "visibility", showPolygons ? "visible" : "none");
        map.setFilter(layer, visible);
      }
      // With the difference raster on, a solid fill would hide it: outline only.
      map.setPaintProperty("changes-fill", "fill-opacity", mode === "cambio" ? 0.06 : 0.3);
      map.setFilter("selected", chosen);
      map.setFilter("selected-casing", chosen);
    }
  }, [ready, mode, showPolygons, hiddenTypes, selectedId]);

  // Swapping the basemap keeps the radar, polygons and selection where they are.
  useEffect(() => {
    const pair = maps.current;
    if (!ready || !pair || shownBasemap.current === basemap) return;
    shownBasemap.current = basemap;
    applyBasemap(pair.after, basemap, RADAR_CREDIT);
    applyBasemap(pair.before, basemap);
  }, [ready, basemap]);

  useEffect(() => {
    if (!ready || !focus || !maps.current) return;
    maps.current.after.fitBounds(focus, { padding: 120, maxZoom: tiles.maxzoom + 1, duration: 700 });
  }, [ready, focus, tiles.maxzoom]);

  const drag = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    const frame = frameRef.current;
    if (!frame || event.buttons === 0) return;
    const box = frame.getBoundingClientRect();
    setPosition(Math.min(98, Math.max(2, ((event.clientX - box.left) / box.width) * 100)));
  }, []);

  const split = mode === "comparar" ? position : mode === "antes" ? 100 : 0;

  return (
    <div className={`compare${bare ? " bare" : ""}`} ref={frameRef}>
      <div className="pane" ref={afterRef} />
      <div className="pane" ref={beforeRef} style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }} />

      {bare ? null : <BasemapSwitch />}

      {mode === "comparar" ? (
        <>
          <span className="tag left">Antes, {beforeLabel}</span>
          <span className="tag right">Después, {afterLabel}</span>
          <div
            className="swipe"
            style={{ left: `${position}%` }}
            role="slider"
            tabIndex={0}
            aria-label="Deslizar entre la imagen de antes y la de después"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(position)}
            onPointerDown={(event) => {
              event.currentTarget.setPointerCapture(event.pointerId);
              drag(event);
            }}
            onPointerMove={drag}
            onKeyDown={(event) => {
              if (event.key === "ArrowLeft") setPosition((value) => Math.max(2, value - 4));
              if (event.key === "ArrowRight") setPosition((value) => Math.min(98, value + 4));
            }}
          >
            <span className="grip" aria-hidden="true">
              <svg width="18" height="12" viewBox="0 0 18 12" fill="none">
                <path d="M6 1 1 6l5 5M12 1l5 5-5 5" stroke="#232323" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          </div>
        </>
      ) : (
        <span className="tag left">
          {mode === "antes" ? `Antes, ${beforeLabel}` : mode === "despues" ? `Después, ${afterLabel}` : `Cambio entre ${beforeLabel} y ${afterLabel}`}
        </span>
      )}
    </div>
  );
}
