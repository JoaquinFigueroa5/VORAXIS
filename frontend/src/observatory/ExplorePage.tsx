import { useQuery } from "@tanstack/react-query";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { Activity, CloudRain, Flame, Satellite } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { BASEMAPS, BasemapSwitch, applyBasemap, basemapSources, useBasemap } from "@/observatory/basemap";
import { boundsCenter, geometryBounds, number, shortDate } from "@/observatory/lib";
import {
  Map as MapLibreMap,
  NavigationControl,
  type GeoJSONSource,
  type MapMouseEvent,
} from "@/observatory/maplibre";
import { ApiError } from "@/services/api";
import { contextService } from "@/services/context.service";
import { locationsService } from "@/services/locations.service";

const WINDOWS = [30, 90, 180] as const;
const RADII = [50, 100, 250] as const;
const FIRE_DAYS = 30; // FIRMS answers at most 31 days per request
const HEAVY_RAIN_MM = 20;

const COLOR = { quake: "#b0305c", fire: "#d2571b", rain: "#1f6fb2", nisar: "#232323" };

const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

function coords(lat: number, lon: number): string {
  return `${number(Math.abs(lat), 2)}° ${lat >= 0 ? "N" : "S"}, ${number(Math.abs(lon), 2)}° ${lon >= 0 ? "E" : "O"}`;
}

function problem(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.message.includes("FIRMS_API_KEY")) return "Falta configurar la clave de NASA FIRMS en el backend.";
    return `La fuente no respondió: ${error.message}`;
  }
  return "La fuente no respondió. Vuelve a intentarlo en un momento.";
}

/** A circle of `km` around the point, as a polygon the map can draw. */
function circle(lon: number, lat: number, km: number, steps = 72): Feature {
  const ring: [number, number][] = [];
  const kmPerLon = 111.32 * Math.cos((lat * Math.PI) / 180);
  for (let i = 0; i <= steps; i += 1) {
    const angle = (i / steps) * 2 * Math.PI;
    ring.push([lon + (km / Math.max(kmPerLon, 1)) * Math.sin(angle), lat + (km / 110.57) * Math.cos(angle)]);
  }
  return { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [ring] } };
}

function Section({ icon, color, title, children }: { icon: ReactNode; color: string; title: string; children: ReactNode }) {
  return (
    <section className="block" aria-label={title}>
      <h2 className="ctx-head">
        <span className="glyph" style={{ color }} aria-hidden="true">
          {icon}
        </span>
        {title}
      </h2>
      {children}
    </section>
  );
}

function Segmented<T extends number>({
  label,
  options,
  value,
  format,
  onChange,
}: {
  label: string;
  options: readonly T[];
  value: T;
  format: (option: T) => string;
  onChange: (option: T) => void;
}) {
  return (
    <div
      className="segmented"
      role="group"
      aria-label={label}
      style={{ "--n": options.length, "--i": Math.max(0, options.indexOf(value)) } as CSSProperties}
    >
      {options.map((option) => (
        <button key={option} aria-pressed={option === value} onClick={() => onChange(option)}>
          {format(option)}
        </button>
      ))}
    </div>
  );
}

interface TimelineRow {
  date: string;
  kind: "nisar" | "quake" | "rain" | "fire";
  title: string;
  detail: string;
}

export function ExplorePage() {
  const [params, setParams] = useSearchParams();
  const lat = params.get("lat") !== null ? Number(params.get("lat")) : null;
  const lon = params.get("lon") !== null ? Number(params.get("lon")) : null;
  const days = (WINDOWS as readonly number[]).includes(Number(params.get("dias"))) ? Number(params.get("dias")) : 90;
  const radius = (RADII as readonly number[]).includes(Number(params.get("radio"))) ? Number(params.get("radio")) : 100;
  const point = lat !== null && lon !== null && Number.isFinite(lat) && Number.isFinite(lon) ? { lat, lon } : null;

  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);
  const fromMap = useRef(false);
  const [ready, setReady] = useState(false);
  const basemap = useBasemap();
  const builtBasemap = useRef(basemap);

  const update = (next: Record<string, string | number | null>) => {
    const search = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) {
      if (value === null) search.delete(key);
      else search.set(key, String(value));
    }
    setParams(search, { replace: true });
  };
  const pick = (picked: { lat: number; lon: number }, viaMap = false) => {
    fromMap.current = viaMap;
    update({ lat: picked.lat.toFixed(4), lon: picked.lon.toFixed(4) });
  };

  const locations = useQuery({ queryKey: ["locations"], queryFn: () => locationsService.list(200) });
  const query = point ? { lat: point.lat, lon: point.lon } : null;
  const nisar = useQuery({
    queryKey: ["ctx", "nisar", point, days],
    queryFn: () => contextService.nisar({ ...query!, days, max_results: 200 }),
    enabled: Boolean(point),
    retry: false,
  });
  const quakes = useQuery({
    queryKey: ["ctx", "quakes", point, days, radius],
    queryFn: () => contextService.earthquakes({ ...query!, days, radius_km: radius }),
    enabled: Boolean(point),
    retry: false,
  });
  const rain = useQuery({
    queryKey: ["ctx", "rain", point, days],
    queryFn: () => contextService.precipitation({ ...query!, days }),
    enabled: Boolean(point),
    retry: false,
  });
  const fires = useQuery({
    queryKey: ["ctx", "fires", point, radius],
    queryFn: () => contextService.fires({ ...query!, days: FIRE_DAYS, radius_km: radius }),
    enabled: Boolean(point),
    retry: false,
  });

  // ---- basemap: swap it in place; lines turn white over imagery
  useEffect(() => {
    const instance = map.current;
    if (!ready || !instance || builtBasemap.current === basemap) return;
    builtBasemap.current = basemap;
    applyBasemap(instance, basemap);
    for (const layer of ["frames-line", "radius-line"]) instance.setPaintProperty(layer, "line-color", BASEMAPS[basemap].ink);
  }, [ready, basemap]);

  // ---- the map: built once, click to pick a point
  useEffect(() => {
    if (!container.current) return;
    const instance = new MapLibreMap({
      container: container.current,
      style: {
        version: 8,
        sources: {
          ...basemapSources(builtBasemap.current),
          frames: { type: "geojson", data: EMPTY },
          radius: { type: "geojson", data: EMPTY },
          quakes: { type: "geojson", data: EMPTY },
          fires: { type: "geojson", data: EMPTY },
          point: { type: "geojson", data: EMPTY },
        },
        layers: [
          { id: "base", type: "raster", source: "base" },
          { id: "frames-fill", type: "fill", source: "frames", paint: { "fill-color": "#232323", "fill-opacity": 0.04 } },
          { id: "frames-line", type: "line", source: "frames", paint: { "line-color": BASEMAPS[builtBasemap.current].ink, "line-width": 1, "line-opacity": 0.45, "line-dasharray": [3, 2] } },
          { id: "radius-fill", type: "fill", source: "radius", paint: { "fill-color": "#a1ffcb", "fill-opacity": 0.16 } },
          { id: "radius-line", type: "line", source: "radius", paint: { "line-color": BASEMAPS[builtBasemap.current].ink, "line-width": 1.5 } },
          { id: "labels", type: "raster", source: "labels" },
          {
            id: "fires",
            type: "circle",
            source: "fires",
            paint: { "circle-radius": 4, "circle-color": COLOR.fire, "circle-stroke-color": "#ffffff", "circle-stroke-width": 1 },
          },
          {
            id: "quakes",
            type: "circle",
            source: "quakes",
            paint: {
              "circle-radius": ["interpolate", ["linear"], ["get", "magnitude"], 2.5, 4, 5, 9, 7, 16],
              "circle-color": COLOR.quake,
              "circle-opacity": 0.8,
              "circle-stroke-color": "#ffffff",
              "circle-stroke-width": 1.5,
            },
          },
          {
            id: "point",
            type: "circle",
            source: "point",
            paint: { "circle-radius": 7, "circle-color": "#a1ffcb", "circle-stroke-color": "#232323", "circle-stroke-width": 2.5 },
          },
        ],
      },
      center: [10, 15],
      zoom: 1.4,
      attributionControl: { compact: true },
    });
    instance.addControl(new NavigationControl({ showCompass: false }), "top-right");
    instance.on("click", (event: MapMouseEvent) => pickRef.current({ lat: event.lngLat.lat, lon: event.lngLat.lng }, true));
    instance.once("load", () => setReady(true));
    map.current = instance;
    return () => {
      map.current = null;
      setReady(false);
      instance.remove();
    };
  }, []);
  const pickRef = useRef(pick);
  pickRef.current = pick;

  const source = (id: string) => map.current?.getSource(id) as GeoJSONSource | undefined;

  // Point and radius; the camera moves only when the point did not come from a click.
  useEffect(() => {
    if (!ready || !map.current) return;
    if (!point) {
      source("point")?.setData(EMPTY);
      source("radius")?.setData(EMPTY);
      return;
    }
    const ring = circle(point.lon, point.lat, radius);
    source("point")?.setData({
      type: "FeatureCollection",
      features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [point.lon, point.lat] } }],
    });
    source("radius")?.setData({ type: "FeatureCollection", features: [ring] });
    if (!fromMap.current) {
      map.current.fitBounds(geometryBounds(ring.geometry as never), { padding: 60, maxZoom: 10, duration: 700 });
    }
    fromMap.current = false;
  }, [ready, point?.lat, point?.lon, radius]); // eslint-disable-line react-hooks/exhaustive-deps

  // NISAR frames: the newest GCOV acquisition of each track and frame over the point.
  const frames = useMemo(() => {
    const seen = new Set<string>();
    const features: Feature[] = [];
    for (const granule of nisar.data?.granules ?? []) {
      if (granule.level !== "GCOV" || !granule.footprint) continue;
      const key = `${granule.track}-${granule.frame}`;
      if (seen.has(key)) continue;
      seen.add(key);
      features.push({ type: "Feature", properties: { track: granule.track }, geometry: granule.footprint as Geometry });
    }
    return features;
  }, [nisar.data]);

  useEffect(() => {
    if (!ready) return;
    source("frames")?.setData({ type: "FeatureCollection", features: point ? frames : [] });
    source("quakes")?.setData({
      type: "FeatureCollection",
      features: point
        ? (quakes.data?.data ?? []).map((event) => ({
            type: "Feature" as const,
            properties: { magnitude: event.magnitude ?? 2.5 },
            geometry: { type: "Point" as const, coordinates: [event.longitude, event.latitude] },
          }))
        : [],
    });
    source("fires")?.setData({
      type: "FeatureCollection",
      features: point
        ? (fires.data?.data ?? []).map((fire) => ({
            type: "Feature" as const,
            properties: {},
            geometry: { type: "Point" as const, coordinates: [fire.longitude, fire.latitude] },
          }))
        : [],
    });
  }, [ready, point, frames, quakes.data, fires.data]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---- everything that happened, newest first
  const timeline = useMemo<TimelineRow[]>(() => {
    const rows: TimelineRow[] = [];
    const passes = new Set<string>();
    for (const granule of nisar.data?.granules ?? []) {
      if (granule.level !== "GCOV") continue;
      const key = `${granule.start.slice(0, 10)}-${granule.track}`;
      if (passes.has(key)) continue;
      passes.add(key);
      rows.push({
        date: granule.start,
        kind: "nisar",
        title: "Pasada de NISAR",
        detail: `Órbita ${granule.track}, ${granule.flight_direction === "ASCENDING" ? "ascendente" : "descendente"}`,
      });
    }
    for (const event of quakes.data?.data ?? []) {
      rows.push({
        date: event.time,
        kind: "quake",
        title: `Sismo M${number(event.magnitude, 1)}`,
        detail: `A ${number(event.distance_km, 0)} km${event.place ? `, ${event.place}` : ""}`,
      });
    }
    for (const day of rain.data?.series ?? []) {
      if ((day.mm ?? 0) >= HEAVY_RAIN_MM) {
        rows.push({ date: `${day.date}T12:00:00Z`, kind: "rain", title: `${number(day.mm, 0)} mm de lluvia`, detail: "En un solo día" });
      }
    }
    for (const [day, count] of Object.entries(fires.data?.detections_by_day ?? {})) {
      rows.push({
        date: `${day}T12:00:00Z`,
        kind: "fire",
        title: `${count} ${count === 1 ? "foco" : "focos"} de fuego`,
        detail: `A menos de ${radius} km`,
      });
    }
    return rows.sort((a, b) => b.date.localeCompare(a.date));
  }, [nisar.data, quakes.data, rain.data, fires.data, radius]);

  const latestGcov = nisar.data?.latest_by_level?.GCOV;
  const pairs = nisar.data?.comparable_pairs ?? [];
  const series = rain.data?.series ?? [];
  const peak = Math.max(1, ...series.map((day) => day.mm ?? 0));
  const elevation = rain.data?.elevation_m;
  const glyph = { nisar: <Satellite size={16} />, quake: <Activity size={16} />, rain: <CloudRain size={16} />, fire: <Flame size={16} /> };

  return (
    <div className="viewer explore">
      <aside className="rail" aria-label="Lo que pasó alrededor del punto">
        <div className="block">
          <p className="label">Explorar un punto</p>
          <h1 className="title" style={{ marginTop: 8 }}>
            {point ? coords(point.lat, point.lon) : "Elige un lugar en el mapa"}
          </h1>
          <p className="quiet" style={{ marginTop: 10 }}>
            {point
              ? elevation != null
                ? `A ${number(elevation, 0)} m sobre el nivel del mar. Haz clic en otro lugar para cambiar el punto.`
                : "Haz clic en otro lugar del mapa para cambiar el punto."
              : "Haz clic en cualquier lugar para ver cuándo pasó NISAR por encima y qué lluvia, incendios y sismos hubo alrededor."}
          </p>
          {!point && (locations.data ?? []).length > 0 ? (
            <div className="picks">
              {(locations.data ?? []).slice(0, 6).map((location) => (
                <button
                  key={location.id}
                  className="btn tonal small"
                  onClick={() => pick(boundsCenter(geometryBounds(location.geometry)))}
                >
                  {location.name}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        {point ? (
          <>
            <div className="block" style={{ display: "grid", gap: 12 }}>
              <Segmented
                label="Ventana de tiempo"
                options={WINDOWS}
                value={days as (typeof WINDOWS)[number]}
                format={(option) => `${option} días`}
                onChange={(option) => update({ dias: option })}
              />
              <Segmented
                label="Radio alrededor del punto"
                options={RADII}
                value={radius as (typeof RADII)[number]}
                format={(option) => `${option} km`}
                onChange={(option) => update({ radio: option })}
              />
            </div>

            <Section icon={glyph.nisar} color={COLOR.nisar} title="Pasadas del radar NISAR">
              {nisar.isLoading ? <p className="quiet">Buscando en el catálogo de NASA…</p> : null}
              {nisar.isError ? <p className="notice problem">{problem(nisar.error)}</p> : null}
              {nisar.data ? (
                nisar.data.total === 0 ? (
                  <p className="quiet">NISAR no tiene imágenes de este punto en los últimos {days} días.</p>
                ) : (
                  <>
                    <p>
                      <span className="figure">{number(nisar.data.count_by_level.GCOV ?? 0, 0)}</span>
                      <span className="quiet"> imágenes listas para comparar</span>
                    </p>
                    <p className="quiet" style={{ marginTop: 8 }}>
                      {latestGcov
                        ? `La más reciente es del ${shortDate(latestGcov.start, true)}${
                            latestGcov.age_days != null ? `, hace ${number(latestGcov.age_days, 0)} días` : ""
                          }. `
                        : ""}
                      Sus huellas están punteadas en el mapa.
                    </p>
                    {pairs.length > 0 ? (
                      <div style={{ display: "grid", gap: 8, marginTop: 16 }}>
                        <p className="label">Pares de fechas que se pueden comparar</p>
                        {pairs.slice(0, 4).map((pair) => (
                          <div key={`${pair.before.product_id}|${pair.after.product_id}`} className="pairline">
                            <span>
                              {shortDate(pair.before.start)} a {shortDate(pair.after.start, true)}
                            </span>
                            <span className="label num">{number(pair.download_gb, 1)} GB</span>
                          </div>
                        ))}
                        <Link className="btn" style={{ marginTop: 8 }} to={`/nuevo?lat=${point.lat}&lon=${point.lon}`}>
                          Crear un análisis aquí
                        </Link>
                      </div>
                    ) : (
                      <p className="label" style={{ marginTop: 12 }}>
                        Aún no hay dos fechas de la misma órbita para comparar; prueba con una ventana más larga.
                      </p>
                    )}
                  </>
                )
              ) : null}
            </Section>

            <Section icon={glyph.rain} color={COLOR.rain} title="Lluvia">
              {rain.isLoading ? <p className="quiet">Consultando NASA POWER…</p> : null}
              {rain.isError ? <p className="notice problem">{problem(rain.error)}</p> : null}
              {rain.data && !rain.data.available ? (
                <p className="quiet">NASA POWER todavía no publica la lluvia de estas fechas.</p>
              ) : null}
              {rain.data?.available ? (
                <>
                  <p>
                    <span className="figure">{number(rain.data.total_mm, 0)} mm</span>
                    <span className="quiet"> en {days} días</span>
                  </p>
                  <p className="quiet" style={{ marginTop: 8 }}>
                    {rain.data.anomaly_pct != null
                      ? `${rain.data.anomaly_pct >= 0 ? "+" : "−"}${number(Math.abs(rain.data.anomaly_pct), 0)} % frente a lo normal para la época. `
                      : ""}
                    {rain.data.max_daily_mm ? `El día más lluvioso, el ${shortDate(rain.data.peak_date)}, cayeron ${number(rain.data.max_daily_mm, 0)} mm.` : ""}
                  </p>
                  <div
                    className="minibars"
                    role="img"
                    aria-label={`Lluvia diaria del ${shortDate(series[0]?.date)} al ${shortDate(series[series.length - 1]?.date)}`}
                    style={{ gap: series.length > 60 ? 1 : 2 }}
                  >
                    {series.map((day) => (
                      <i
                        key={day.date}
                        title={`${shortDate(day.date)}: ${number(day.mm, 0)} mm`}
                        style={{ height: `${Math.max(2, ((day.mm ?? 0) / peak) * 100)}%` }}
                      />
                    ))}
                  </div>
                  <div className="minibars-axis label">
                    <span>{shortDate(series[0]?.date)}</span>
                    <span>{shortDate(series[series.length - 1]?.date)}</span>
                  </div>
                </>
              ) : null}
            </Section>

            <Section icon={glyph.fire} color={COLOR.fire} title={`Incendios en los últimos ${FIRE_DAYS} días`}>
              {fires.isLoading ? <p className="quiet">Consultando NASA FIRMS…</p> : null}
              {fires.isError ? <p className="notice problem">{problem(fires.error)}</p> : null}
              {fires.data ? (
                fires.data.total === 0 ? (
                  <p className="quiet">Ningún foco de fuego activo a menos de {radius} km.</p>
                ) : (
                  <>
                    <p>
                      <span className="figure">{number(fires.data.total, 0)}</span>
                      <span className="quiet"> focos a menos de {radius} km</span>
                    </p>
                    <p className="quiet" style={{ marginTop: 8 }}>
                      En {number(Object.keys(fires.data.detections_by_day).length, 0)} días distintos. El más intenso emitió{" "}
                      {number(fires.data.max_frp_mw, 1)} MW.
                    </p>
                  </>
                )
              ) : null}
            </Section>

            <Section icon={glyph.quake} color={COLOR.quake} title="Sismos">
              {quakes.isLoading ? <p className="quiet">Consultando USGS…</p> : null}
              {quakes.isError ? <p className="notice problem">{problem(quakes.error)}</p> : null}
              {quakes.data ? (
                quakes.data.total === 0 ? (
                  <p className="quiet">Ningún sismo de magnitud 2,5 o más a menos de {radius} km.</p>
                ) : (
                  <>
                    <p>
                      <span className="figure">{number(quakes.data.total, 0)}</span>
                      <span className="quiet"> sismos a menos de {radius} km</span>
                    </p>
                    {quakes.data.strongest ? (
                      <p className="quiet" style={{ marginTop: 8 }}>
                        El más fuerte, M{number(quakes.data.strongest.magnitude, 1)} el{" "}
                        {shortDate(quakes.data.strongest.time, true)}, a {number(quakes.data.strongest.distance_km, 0)} km
                        {quakes.data.strongest.place ? ` (${quakes.data.strongest.place})` : ""}.
                      </p>
                    ) : null}
                  </>
                )
              ) : null}
            </Section>

            <section className="block" aria-label="Cronología">
              <h2 className="ctx-head">Cronología</h2>
              {timeline.length === 0 ? (
                <p className="quiet">Nada que mostrar todavía en esta ventana.</p>
              ) : (
                <ol className="chrono">
                  {timeline.slice(0, 40).map((row, index) => (
                    <li key={`${row.kind}-${row.date}-${index}`}>
                      <span className="when label">{shortDate(row.date)}</span>
                      <span className="glyph" style={{ color: COLOR[row.kind] }} aria-hidden="true">
                        {glyph[row.kind]}
                      </span>
                      <span>
                        <strong>{row.title}</strong>
                        <span className="label"> {row.detail}</span>
                      </span>
                    </li>
                  ))}
                </ol>
              )}
              {timeline.length > 40 ? <p className="label">Se muestran los 40 eventos más recientes.</p> : null}
            </section>
          </>
        ) : null}
      </aside>

      <div className="stage">
        <div className="compare">
          <div className="pane" ref={container} aria-label="Mapa: haz clic para elegir un punto" />
          <BasemapSwitch />
          {point ? (
            <div className="map-legend" aria-hidden="true">
              <span><i className="dot" style={{ background: "#a1ffcb", boxShadow: "0 0 0 2px #232323" }} />Punto</span>
              <span><i className="ring" />{radius} km</span>
              {frames.length > 0 ? <span><i className="frame" />Huella NISAR</span> : null}
              {(fires.data?.total ?? 0) > 0 ? <span><i className="dot" style={{ background: COLOR.fire }} />Fuego</span> : null}
              {(quakes.data?.total ?? 0) > 0 ? <span><i className="dot big" style={{ background: COLOR.quake }} />Sismo</span> : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
