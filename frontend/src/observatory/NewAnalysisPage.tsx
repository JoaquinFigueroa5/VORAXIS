import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BASEMAPS, BasemapSwitch, applyBasemap, basemapSources, useBasemap } from "@/observatory/basemap";
import { Map as MapLibreMap, NavigationControl, type GeoJSONSource } from "@/observatory/maplibre";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { DEFAULT_MULTILOOK, STAGE, failureText, jobForPair, launchAnalysis, useIngestTasks, useJobs } from "@/observatory/downloads";
import { boundsCenter, geometryBounds, number, shortDate } from "@/observatory/lib";
import { ApiError } from "@/services/api";
import { contextService } from "@/services/context.service";
import { ingestService } from "@/services/ingest.service";
import { locationsService } from "@/services/locations.service";
import type { NisarPair } from "@/types/context";
import type { IngestTask } from "@/types/ingest";

function message(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error ? error.message : "Ocurrió un error inesperado.";
}

export function NewAnalysisPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);
  const alive = useRef(true);
  const [params] = useSearchParams();

  const [locationId, setLocationId] = useState("");
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [pair, setPair] = useState<NisarPair | null>(null);
  /** Tasks this page queued, oldest acquisition first; their progress comes from the shared downloads query. */
  const [queued, setQueued] = useState<IngestTask[]>([]);
  const [running, setRunning] = useState(false);
  const launched = useRef(false);
  const [mapReady, setMapReady] = useState(false);
  const basemap = useBasemap();
  const builtBasemap = useRef(basemap);
  const [problem, setProblem] = useState<string | null>(null);

  const ingest = useIngestTasks();
  const jobs = useJobs(running);
  const tasks = useMemo(
    () => queued.map((task) => ingest.data?.find((item) => item.id === task.id) ?? task),
    [queued, ingest.data],
  );

  const locations = useQuery({ queryKey: ["locations"], queryFn: () => locationsService.list(200) });
  const location = locations.data?.find((item) => item.id === locationId) ?? null;
  const centre = useMemo(() => (location ? boundsCenter(geometryBounds(location.geometry)) : null), [location]);

  const coverage = useQuery({
    queryKey: ["pairs", centre],
    queryFn: () => contextService.nisar({ lat: centre?.lat ?? 0, lon: centre?.lon ?? 0, days: 120, level: "GCOV", max_results: 200 }),
    enabled: Boolean(centre),
    retry: false,
  });

  useEffect(() => {
    alive.current = true;
    if (!container.current) return;
    const instance = new MapLibreMap({
      container: container.current,
      style: {
        version: 8,
        sources: {
          ...basemapSources(builtBasemap.current),
          zones: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        },
        layers: [
          { id: "base", type: "raster", source: "base" },
          { id: "labels", type: "raster", source: "labels" },
          { id: "zones-fill", type: "fill", source: "zones", paint: { "fill-color": ["case", ["get", "active"], "#a1ffcb", "#232323"], "fill-opacity": ["case", ["get", "active"], 0.28, 0.05] } },
          { id: "zones-line", type: "line", source: "zones", paint: { "line-color": BASEMAPS[builtBasemap.current].ink, "line-width": ["case", ["get", "active"], 2.5, 1] } },
        ],
      },
      center: [0, 15],
      zoom: 1.6,
    });
    instance.addControl(new NavigationControl({ showCompass: false }), "top-right");
    instance.once("load", () => setMapReady(true));
    // Coming from Explorar: frame the chosen point and offer to save that view as a zone.
    const lat = Number(params.get("lat"));
    const lon = Number(params.get("lon"));
    if (params.get("lat") && Number.isFinite(lat) && Number.isFinite(lon)) {
      instance.jumpTo({ center: [lon, lat], zoom: 9.2 });
      setCreating(true);
      setName(`Zona en ${number(Math.abs(lat), 2)}° ${lat >= 0 ? "N" : "S"}, ${number(Math.abs(lon), 2)}° ${lon >= 0 ? "E" : "O"}`);
    }
    map.current = instance;
    return () => {
      alive.current = false;
      map.current = null;
      setMapReady(false);
      instance.remove();
    };
  }, []);

  useEffect(() => {
    const instance = map.current;
    if (!mapReady || !instance || builtBasemap.current === basemap) return;
    builtBasemap.current = basemap;
    applyBasemap(instance, basemap);
    instance.setPaintProperty("zones-line", "line-color", BASEMAPS[basemap].ink);
  }, [mapReady, basemap]);

  // Draw every stored zone; the chosen one is highlighted and framed.
  useEffect(() => {
    const instance = map.current;
    if (!instance || !locations.data) return;
    const draw = () => {
      (instance.getSource("zones") as GeoJSONSource | undefined)?.setData({
        type: "FeatureCollection",
        features: locations.data.map((item) => ({
          type: "Feature",
          geometry: item.geometry,
          properties: { active: item.id === locationId },
        })),
      });
      if (location) instance.fitBounds(geometryBounds(location.geometry), { padding: 60, duration: 600 });
    };
    if (instance.isStyleLoaded()) draw();
    else instance.once("load", draw);
  }, [locations.data, locationId, location]);

  async function createZone() {
    const instance = map.current;
    if (!instance) return;
    setProblem(null);
    const view = instance.getBounds();
    try {
      const created = await locationsService.create({
        name: name.trim(),
        bbox: [view.getWest(), view.getSouth(), view.getEast(), view.getNorth()],
      });
      await queryClient.invalidateQueries({ queryKey: ["locations"] });
      setLocationId(created.id);
      setCreating(false);
      setName("");
      setPair(null);
    } catch (error) {
      setProblem(
        message(error).includes("maximum is 3")
          ? "La vista del mapa es demasiado grande. Acércate hasta ver un área de unos 300 km de lado como máximo y vuelve a intentarlo."
          : message(error).includes("already exists")
            ? "Ya hay una zona con ese nombre. Elige otro."
            : message(error),
      );
    }
  }

  async function run() {
    if (!location || !pair) return;
    setRunning(true);
    setProblem(null);
    launched.current = false;
    try {
      const created = await ingestService.create({
        location_id: location.id,
        product_ids: [pair.before.product_id, pair.after.product_id],
        multilook: DEFAULT_MULTILOOK,
      });
      setQueued(created);
      await queryClient.invalidateQueries({ queryKey: ["ingest"] });
    } catch (error) {
      setProblem(message(error));
      setRunning(false);
    }
  }

  // While the user stays here, compare as soon as both images are ready. If they
  // leave, the downloads menu in the header picks it up.
  useEffect(() => {
    if (!running || !location || tasks.length !== 2 || launched.current) return;
    if (tasks.some((task) => task.status === "QUEUED" || task.status === "RUNNING")) return;
    const failed = tasks.find((task) => task.status === "FAILED");
    if (failed) {
      setProblem(failureText(failed.error));
      setRunning(false);
      return;
    }
    const [before, after] = tasks.map((task) => task.result?.observation_id ?? "");
    const existing = jobForPair(jobs.data, { before, after });
    launched.current = true;
    if (existing) {
      navigate(`/analisis/${existing.id}`);
      return;
    }
    launchAnalysis(location.id, { before, after })
      .then(async (accepted) => {
        await queryClient.invalidateQueries({ queryKey: ["jobs"] });
        navigate(`/analisis/${accepted.job_id}`);
      })
      .catch((error: unknown) => {
        if (!alive.current) return;
        setProblem(message(error));
        setRunning(false);
      });
  }, [running, location, tasks, jobs.data, navigate, queryClient]);

  const pairs = coverage.data?.comparable_pairs ?? [];

  return (
    <div className="wizard">
      <div className="steps">
        <div className="block">
          <h1 className="title">Nuevo análisis</h1>
          <p className="quiet" style={{ marginTop: 10 }}>
            Elige una zona y dos pasadas del radar. Voraxis descarga las imágenes, las compara y te lleva al resultado.
          </p>
        </div>

        <div className={`block step${location ? " done" : ""}`}>
          <span className="n">1</span>
          <div>
          <h2>La zona</h2>
          <label className="field">
            Zonas guardadas
            <select
              value={locationId}
              disabled={running}
              onChange={(event) => {
                setLocationId(event.target.value);
                setPair(null);
                setProblem(null);
              }}
            >
              <option value="">Elige una zona…</option>
              {(locations.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                  {item.country ? ` (${item.country})` : ""}
                </option>
              ))}
            </select>
          </label>

          {creating ? (
            <div style={{ display: "grid", gap: "0.6rem", marginTop: "0.9rem" }}>
              <p className="quiet">Mueve y acerca el mapa hasta encuadrar la zona. Se guardará lo que se ve ahora.</p>
              <label className="field">
                Nombre de la zona
                <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Por ejemplo, Costa de Machilipatnam" />
              </label>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button className="btn small" disabled={!name.trim()} onClick={createZone}>Guardar esta vista como zona</button>
                <button className="btn tonal small" onClick={() => setCreating(false)}>Cancelar</button>
              </div>
            </div>
          ) : (
            <button className="btn tonal small" style={{ marginTop: 12 }} disabled={running} onClick={() => setCreating(true)}>
              Crear una zona nueva en el mapa
            </button>
          )}
          </div>
        </div>

        <div className={`block step${pair ? " done" : ""}`}>
          <span className="n">2</span>
          <div>
          <h2>Las dos fechas</h2>
          {!location ? <p className="quiet">Primero elige una zona.</p> : null}
          {location && coverage.isLoading ? <p className="quiet">Buscando pasadas de NISAR sobre la zona…</p> : null}
          {location && coverage.isError ? (
            <p className="notice problem">El catálogo de NASA no respondió. Espera un momento y vuelve a elegir la zona.</p>
          ) : null}
          {location && coverage.data && pairs.length === 0 ? (
            <p className="notice">
              NISAR no tiene dos pasadas comparables sobre el centro de esta zona en los últimos 120 días. Prueba con otra zona.
            </p>
          ) : null}
          <div style={{ display: "grid", gap: "0.5rem" }}>
            {pairs.slice(0, 8).map((option) => {
              const key = `${option.before.product_id}|${option.after.product_id}`;
              const chosen = pair ? `${pair.before.product_id}|${pair.after.product_id}` === key : false;
              return (
                <button key={key} className="pairrow" aria-pressed={chosen} disabled={running} onClick={() => setPair(option)}>
                  <span className="when">
                    {shortDate(option.before.start)} a {shortDate(option.after.start, true)}
                  </span>
                  <span className="num label">{number(option.download_gb, 1)} GB</span>
                  <span className="label" style={{ gridColumn: "1 / -1" }}>
                    {number(option.interval_days, 0)} días de diferencia, órbita {option.track}
                    {option.same_processing_version ? "" : ", procesadas con versiones distintas"}
                  </span>
                </button>
              );
            })}
          </div>
          </div>
        </div>

        <div className="block step">
          <span className="n">3</span>
          <div>
          <h2>Descargar y comparar</h2>
          {tasks.length === 0 ? (
            <p className="quiet">
              La descarga puede tardar varios minutos por imagen la primera vez. Si ya están descargadas, son unos segundos.
            </p>
          ) : (
            <p className="quiet" style={{ marginBottom: "0.9rem" }}>
              Puedes salir de esta pantalla: la descarga sigue en el servidor y la ves en Descargas, arriba a la derecha.
            </p>
          )}
          <div style={{ display: "grid", gap: "0.8rem", marginBottom: tasks.length ? "0.9rem" : 0 }}>
            {tasks.map((task, index) => (
              <div key={task.id}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, marginBottom: 8 }}>
                  <span>{index === 0 ? "Imagen de antes" : "Imagen de después"}</span>
                  <span className="quiet">
                    {task.status === "FAILED" ? "Falló" : STAGE[task.stage ?? "QUEUED"]}
                    {task.detail ? `, ${task.detail}` : ""}
                  </span>
                </div>
                <div className="bar"><i style={{ transform: `scaleX(${task.progress / 100})` }} /></div>
              </div>
            ))}
          </div>
          {problem ? <p className="notice problem" style={{ marginBottom: "0.8rem" }}>{problem}</p> : null}
          <button className="btn" disabled={!location || !pair || running} onClick={run}>
            {running ? "Preparando las imágenes…" : "Descargar y comparar"}
          </button>
          </div>
        </div>
      </div>

      <div className="wizard-map compare" style={{ minHeight: 0 }}>
        <div className="pane" ref={container} />
        <BasemapSwitch />
      </div>
    </div>
  );
}
