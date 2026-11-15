import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { CompareMap } from "@/observatory/CompareMap";
import { area, number, shortDate, signedDb, typeStyle } from "@/observatory/lib";
import { apiFetch } from "@/services/api";
import { insightsService } from "@/services/insights.service";
import { jobsService } from "@/services/jobs.service";
import { locationsService } from "@/services/locations.service";
import { observationsService } from "@/services/observations.service";
import type { TileDescription } from "@/types/change";
import type { ProcessingJob } from "@/types/job";

const STATUS: Record<string, string> = {
  PENDING: "En cola",
  RUNNING: "En curso",
  COMPLETED: "Listo",
  FAILED: "No terminó",
  CANCELLED: "Cancelado",
};

const LIST_LIMIT = 6;

function mainType(job: ProcessingJob): string | null {
  const types = (job.result?.change_types ?? {}) as Record<string, number>;
  const [top] = Object.entries(types).sort((a, b) => b[1] - a[1]);
  return top ? top[0] : null;
}

function changeCount(job: ProcessingJob): number {
  return typeof job.result?.change_events === "number" ? job.result.change_events : 0;
}

interface MomentsModule {
  mount: (element: Element) => Promise<{ destroy?: () => void } | null>;
}

const MOMENTS_URL = "/assets/moments/moments.js";

type MomentsWindow = Window & { __momentsManual?: boolean; __voraxisMoments?: MomentsModule };

/**
 * The kit's loader lives in public/ as plain files, which Vite will not bundle, so the
 * browser loads it through a module script. It mounts only what React hands it.
 */
function loadMoments(): Promise<MomentsModule> {
  const host = window as MomentsWindow;
  host.__momentsManual = true;
  if (host.__voraxisMoments) return Promise.resolve(host.__voraxisMoments);
  return new Promise((resolve, reject) => {
    const done = () => (host.__voraxisMoments ? resolve(host.__voraxisMoments) : reject(new Error("moments")));
    window.addEventListener("voraxis-moments", done, { once: true });
    const script = document.createElement("script");
    script.type = "module";
    script.textContent = `import(${JSON.stringify(MOMENTS_URL)}).then((m) => { window.__voraxisMoments = m; }).finally(() => dispatchEvent(new Event("voraxis-moments")));`;
    document.head.appendChild(script);
  });
}

/**
 * One statement, mounted by the dealt moment (word-highlight from the taste kit):
 * its words rest at half ink and turn to ink as it crosses the screen, the
 * <strong> part to the accent. Without script, or with reduced motion, it is all ink.
 */
function Statement() {
  const section = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const host = section.current;
    if (!host) return;
    let api: { destroy?: () => void } | null = null;
    let gone = false;
    loadMoments()
      .then((moments) => moments.mount(host))
      .then((mounted) => {
        if (gone) mounted?.destroy?.();
        else api = mounted;
      })
      .catch(() => {
        /* without the moment the statement simply stays in full ink */
      });
    return () => {
      gone = true;
      api?.destroy?.();
    };
  }, []);

  return (
    <section className="statement" ref={section} data-moment="word-highlight" aria-labelledby="statement-h">
      <div className="wrap">
        <h2 id="statement-h" className="mo-wh__text">
          El radar ve de noche y a través de las nubes. Dos pasadas separadas por doce días bastan para saber dónde{" "}
          <strong>cambió el terreno.</strong>
        </h2>
        <dl className="facts-row">
          <div>
            <dt className="num">12 días</dt>
            <dd>entre una pasada de NISAR y la siguiente sobre el mismo lugar</dd>
          </div>
          <div>
            <dt className="num">10 m</dt>
            <dd>de lado mide cada píxel de la imagen que se compara</dd>
          </div>
          <div>
            <dt className="num">24 cm</dt>
            <dd>de longitud de onda: la banda L atraviesa nubes, humo y follaje ligero</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}

export function HomePage() {
  const navigate = useNavigate();
  const [all, setAll] = useState(false);

  const jobs = useQuery({ queryKey: ["jobs"], queryFn: () => jobsService.list({ limit: 100 }), refetchInterval: 10_000 });
  const locations = useQuery({ queryKey: ["locations"], queryFn: () => locationsService.list(200) });
  const observations = useQuery({ queryKey: ["observations"], queryFn: () => observationsService.list({ limit: 200 }) });

  const place = new Map((locations.data ?? []).map((location) => [location.id, location]));
  const date = new Map((observations.data ?? []).map((observation) => [observation.id, observation.acquisition_date]));

  // The hero shows the newest finished analysis that found something.
  const featured = (jobs.data ?? []).find((job) => job.status === "COMPLETED" && changeCount(job) > 0) ?? null;
  const tiles = useQuery({
    queryKey: ["job", featured?.id, "tiles"],
    queryFn: () => apiFetch<TileDescription>(`/jobs/${featured?.id}/tiles`),
    enabled: Boolean(featured),
    staleTime: Infinity,
  });
  const insights = useQuery({
    queryKey: ["job", featured?.id, "insights"],
    queryFn: () => insightsService.forJob(featured?.id as string),
    enabled: Boolean(featured),
  });

  const featuredPlace = featured ? place.get(featured.location_id) : undefined;
  const before = insights.data?.acquisitions.before ?? null;
  const after = insights.data?.acquisitions.after ?? null;
  const top = insights.data?.by_type[0];
  const rain = insights.data?.precipitation[0];

  return (
    <>
      <section className="hero" data-enter>
        <div className="wrap">
          <div className="copy hero-text">
            <h1>Mapas de cambio del terreno con el radar NISAR</h1>
            <p className="lead">
              Elige una zona y dos fechas. Voraxis compara las dos pasadas del satélite y marca qué se inundó, se
              quemó o perdió vegetación.
            </p>
            <div className="actions">
              <Link className="btn" to="/nuevo">
                Crear un análisis
              </Link>
              {featured ? (
                <Link className="btn tonal" to={`/analisis/${featured.id}`}>
                  Ver el último análisis
                </Link>
              ) : null}
            </div>
            <p className="proof">
              {top && featuredPlace
                ? `En ${featuredPlace.name}: ${area(top.area_km2)} de ${typeStyle(top.change_type).label.toLowerCase()} entre el ${shortDate(before)} y el ${shortDate(after, true)}.`
                : "NISAR repite cada pasada a los 12 días y mide el terreno en píxeles de 10 metros."}
            </p>
          </div>

          <div className="art">
            <div className="window">
              <div className="bar-top">
                <strong>{featuredPlace?.name ?? "Zona de estudio"}</strong>
                <span className="label">
                  {before && after ? `${shortDate(before)} a ${shortDate(after, true)}` : "Dos pasadas del radar"}
                </span>
              </div>
              {featured && tiles.data && before && after ? (
                <CompareMap
                  bare
                  jobId={featured.id}
                  tiles={tiles.data}
                  mode="comparar"
                  showPolygons
                  hiddenTypes={[]}
                  selectedId={null}
                  onSelect={() => navigate(`/analisis/${featured.id}`)}
                  focus={null}
                  beforeLabel={shortDate(before)}
                  afterLabel={shortDate(after)}
                />
              ) : (
                <div className="compare" />
              )}
            </div>

            {top ? (
              <div className="result">
                <span className="chip">
                  <i style={{ background: typeStyle(top.change_type).color }} />
                  {typeStyle(top.change_type).label}
                </span>
                <p className="value">{area(top.area_km2)}</p>
                <p className="label">en {number(top.count, 0)} áreas detectadas</p>
                <dl>
                  <dt>Cambio medio de la señal</dt>
                  <dd className="num">{signedDb(top.mean_change_db)}</dd>
                  {rain?.total_mm != null ? (
                    <>
                      <dt>Lluvia en el intervalo</dt>
                      <dd className="num">{number(rain.total_mm, 0)} mm</dd>
                    </>
                  ) : null}
                </dl>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <Statement />

      <section className="saved" id="analisis" aria-labelledby="analisis-h">
        <div className="wrap">
          <div className="head">
            <h2 id="analisis-h">Análisis guardados</h2>
          </div>

          {jobs.isLoading ? <p className="quiet">Cargando análisis…</p> : null}
          {jobs.isError ? (
            <p className="notice problem">
              La API no responde. Comprueba que el backend esté encendido y recarga la página.
            </p>
          ) : null}
          {jobs.data && jobs.data.length === 0 ? (
            <p className="notice">Todavía no hay análisis. Crea el primero eligiendo una zona y dos fechas del radar.</p>
          ) : null}

          {jobs.data && jobs.data.length > 0 ? (
            <div>
              <table className="runs">
                <thead>
                  <tr>
                    <th>Zona</th>
                    <th>Fechas comparadas</th>
                    <th>Áreas con cambio</th>
                    <th>Cambio más frecuente</th>
                    <th>Estado</th>
                    <th aria-hidden="true" />
                  </tr>
                </thead>
                <tbody>
                  {jobs.data.slice(0, all ? undefined : LIST_LIMIT).map((job) => {
                    const location = place.get(job.location_id);
                    const type = mainType(job);
                    const open = () => navigate(`/analisis/${job.id}`);
                    return (
                      <tr
                        key={job.id}
                        className="link"
                        tabIndex={0}
                        onClick={open}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") open();
                        }}
                      >
                        <td>
                          <span className="place">{location?.name ?? "Zona sin nombre"}</span>
                          {location?.country ? <span className="quiet"> {location.country}</span> : null}
                        </td>
                        <td>
                          {shortDate(date.get(job.before_observation_id))} a{" "}
                          {shortDate(date.get(job.after_observation_id), true)}
                        </td>
                        <td className="num">{job.status === "COMPLETED" ? number(changeCount(job), 0) : ""}</td>
                        <td>
                          {type ? (
                            <span className="chip">
                              <i style={{ background: typeStyle(type).color }} />
                              {typeStyle(type).label}
                            </span>
                          ) : null}
                        </td>
                        <td className="quiet">{STATUS[job.status] ?? job.status}</td>
                        <td style={{ textAlign: "right" }}>
                          <span className="go" aria-hidden="true">
                            <svg width="18" height="12" viewBox="0 0 18 12" fill="none">
                              <path d="M1 6h15M11 1l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {jobs.data.length > LIST_LIMIT ? (
                <button className="btn tonal" style={{ marginTop: 24 }} onClick={() => setAll(!all)}>
                  {all ? "Mostrar menos análisis" : `Mostrar los ${jobs.data.length - LIST_LIMIT} análisis restantes`}
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </section>

    </>
  );
}
