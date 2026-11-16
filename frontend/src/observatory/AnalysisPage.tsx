import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { coded, t } from "@/i18n";
import { ChangePanel } from "@/observatory/ChangePanel";
import { CompareMap, type ViewMode } from "@/observatory/CompareMap";
import { IntervalStrip } from "@/observatory/IntervalStrip";
import { addDays, area, boundsCenter, geometryBounds, isoDay, number, shortDate, signedDb, typeStyle, type Bounds } from "@/observatory/lib";
import { apiFetch } from "@/services/api";
import { changesService } from "@/services/changes.service";
import { contextService } from "@/services/context.service";
import { insightsService } from "@/services/insights.service";
import { jobsService } from "@/services/jobs.service";
import { locationsService } from "@/services/locations.service";
import { observationsService } from "@/services/observations.service";
import { useInterface } from "@/stores/interface";
import type { TileDescription } from "@/types/change";
import { FINAL_JOB_STATUSES } from "@/types/job";

const MODES: { id: ViewMode; label: string }[] = [
  { id: "comparar", label: "Comparar" },
  { id: "cambio", label: "Cambio" },
  { id: "antes", label: "Antes" },
  { id: "despues", label: "Después" },
];

const STEP_LABELS: Record<string, string> = {
  DOWNLOADING: "Trayendo las imágenes",
  PREPROCESSING: "Leyendo las imágenes",
  ALIGNMENT: "Alineando las dos fechas",
  CHANGE_DETECTION: "Detectando cambios",
  VECTORIZATION: "Delimitando las áreas",
  EVIDENCE_ANALYSIS: "Buscando sismos, incendios y lluvia",
  EXPORTING: "Guardando los mapas",
};

/** Known failures come as a code (`cancelled_by_user`); anything else is the worker's own message. */
function jobError(message: string | null): string {
  if (!message) return t("job.error.generic");
  return /^[a-z_]+$/.test(message) ? t(`job.error.${message}`, null, t("job.error.generic")) : message;
}

export function AnalysisPage() {
  const { id = "" } = useParams();
  const [mode, setMode] = useState<ViewMode>("comparar");
  const [showPolygons, setShowPolygons] = useState(true);
  const [hidden, setHidden] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [focus, setFocus] = useState<Bounds | null>(null);
  const [order, setOrder] = useState<"area" | "score">("area");
  const scientific = useInterface((state) => state.scientific);

  const job = useQuery({
    queryKey: ["job", id],
    queryFn: () => jobsService.get(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && !FINAL_JOB_STATUSES.includes(status) ? 2000 : false;
    },
  });
  const done = job.data?.status === "COMPLETED";

  const tiles = useQuery({
    queryKey: ["job", id, "tiles"],
    queryFn: () => apiFetch<TileDescription>(`/jobs/${id}/tiles`),
    enabled: done,
    staleTime: Infinity,
  });
  const insights = useQuery({
    queryKey: ["job", id, "insights"],
    queryFn: () => insightsService.forJob(id),
    enabled: done,
  });
  const location = useQuery({
    queryKey: ["location", job.data?.location_id],
    queryFn: () => locationsService.get(job.data?.location_id as string),
    enabled: Boolean(job.data?.location_id),
  });
  // The before-side observation carries the product metadata the header shows.
  const beforeObservation = useQuery({
    queryKey: ["observation", job.data?.before_observation_id],
    queryFn: () => observationsService.get(job.data?.before_observation_id as string),
    enabled: Boolean(job.data?.before_observation_id),
    staleTime: Infinity,
  });

  const shown = useMemo(
    () => (insights.data?.by_type ?? []).map((row) => row.change_type).filter((type) => !hidden.includes(type)),
    [insights.data, hidden],
  );
  const list = useQuery({
    queryKey: ["job", id, "changes", order, shown],
    queryFn: () => changesService.page({ job_id: id, sort: order, limit: 40, change_type: shown }),
    enabled: done && shown.length > 0,
  });

  const before = insights.data?.acquisitions.before ?? null;
  const after = insights.data?.acquisitions.after ?? null;
  const intervalDays = useMemo(() => {
    if (!before || !after) return null;
    return (new Date(after).getTime() - new Date(before).getTime()) / 86_400_000;
  }, [before, after]);
  const centre = useMemo(
    () => (location.data ? boundsCenter(geometryBounds(location.data.geometry)) : null),
    [location.data],
  );
  const timeline = useQuery({
    queryKey: ["timeline", centre, before, after],
    queryFn: () =>
      contextService.timeline({
        lat: centre?.lat ?? 0,
        lon: centre?.lon ?? 0,
        start: addDays(isoDay(before as string), -7),
        end: isoDay(after as string),
        radius_km: 100,
      }),
    enabled: Boolean(centre && before && after),
    staleTime: Infinity,
    retry: false,
  });

  if (job.isLoading) return <div className="page"><div className="inner quiet">Abriendo el análisis…</div></div>;
  if (job.isError || !job.data) {
    return (
      <div className="page">
        <div className="inner">
          <p className="notice problem">Este análisis no existe o la API no responde.</p>
          <p style={{ marginTop: "1rem" }}>
            <Link className="btn tonal" to="/">Ver todos los análisis</Link>
          </p>
        </div>
      </div>
    );
  }

  if (!done) {
    const failed = job.data.status === "FAILED" || job.data.status === "CANCELLED";
    return (
      <div className="page">
        <div className="inner" style={{ maxWidth: 560 }}>
          <h1 className="title">
            {failed ? "El análisis no terminó" : "Analizando las dos fechas"}
          </h1>
          {failed ? (
            <p className="notice problem" style={{ marginTop: "1rem" }}>
              {jobError(job.data.error_message)}
            </p>
          ) : (
            <>
              <p className="quiet" style={{ margin: "12px 0 20px" }}>
                {STEP_LABELS[job.data.current_step ?? ""] ?? "En cola, esperando su turno"}.
              </p>
              <div className="bar"><i style={{ transform: `scaleX(${job.data.progress / 100})` }} /></div>
              <p className="label" style={{ marginTop: 12 }}>
                Suele tardar entre unos segundos y dos minutos. Esta página se actualiza sola.
              </p>
            </>
          )}
        </div>
      </div>
    );
  }

  const totals = insights.data?.totals;
  const largestType = Math.max(1, ...(insights.data?.by_type ?? []).map((row) => row.area_km2));
  const warnings = insights.data?.warnings ?? [];
  const sources = Object.entries(insights.data?.sources ?? {}).filter(([, info]) => info.status !== "ok");

  const pick = (changeId: string | null) => setSelected(changeId);

  return (
    <div className={`viewer${selected ? " with-detail" : ""}`}>
      <aside className="rail" aria-label="Resumen del análisis">
        <div className="block">
          <p className="label">
            {shortDate(before)} a {shortDate(after, true)}
            {location.data?.country ? `, ${location.data.country}` : ""}
          </p>
          <h1 className="title" style={{ margin: "8px 0 0" }}>
            {location.data?.name ?? "Zona de estudio"}
          </h1>
          {totals ? (
            <>
              <p className="figure" style={{ marginTop: 28 }}>{area(totals.area_km2)}</p>
              <p className="quiet" style={{ marginTop: 8 }}>
                con cambios, en {number(totals.changes, 0)} áreas. Señal {String(job.data.result?.polarization ?? "HH")},
                umbral de {number(totals.threshold_db, 1)} dB.
              </p>
              <dl className="facts" style={{ marginTop: 20 }}>
                <div>
                  <dt>Área afectada</dt>
                  <dd className="num">{area(totals.area_km2)}</dd>
                </div>
                <div>
                  <dt>Intensidad relativa</dt>
                  <dd className="num">{number(totals.mean_score, 2)}</dd>
                </div>
                <div>
                  <dt>Píxeles válidos</dt>
                  <dd className="num">
                    {totals.valid_pixel_percentage != null
                      ? `${number(totals.valid_pixel_percentage, 1)} %`
                      : "sin dato"}
                  </dd>
                </div>
                <div>
                  <dt>Intervalo</dt>
                  <dd className="num">
                    {intervalDays != null ? `${number(intervalDays, 0)} días` : "sin dato"}
                  </dd>
                </div>
              </dl>
              {scientific ? (
                <dl className="facts" style={{ marginTop: 16 }}>
                  <div>
                    <dt>Producto</dt>
                    <dd className="num">{beforeObservation.data?.product_type ?? "sin dato"}</dd>
                  </div>
                  <div>
                    <dt>Madurez</dt>
                    <dd className="num">{beforeObservation.data?.maturity ?? "sin dato"}</dd>
                  </div>
                  <div>
                    <dt>Polarización</dt>
                    <dd className="num">
                      {beforeObservation.data?.polarization?.join(" · ") ??
                        String(job.data.result?.polarization ?? "sin dato")}
                    </dd>
                  </div>
                  <div>
                    <dt>Órbita</dt>
                    <dd className="num">{beforeObservation.data?.orbit_direction ?? "sin dato"}</dd>
                  </div>
                  <div>
                    <dt>Versión de proceso</dt>
                    <dd className="num">{beforeObservation.data?.processing_version ?? "sin dato"}</dd>
                  </div>
                  <div>
                    <dt>Análisis</dt>
                    <dd className="num">{id.slice(0, 8)}</dd>
                  </div>
                </dl>
              ) : null}
            </>
          ) : null}
        </div>

        <div className="block">
          <div
            className="segmented"
            role="group"
            aria-label="Qué mostrar en el mapa"
            style={{ "--n": MODES.length, "--i": MODES.findIndex((option) => option.id === mode) } as React.CSSProperties}
          >
            {MODES.map((option) => (
              <button key={option.id} aria-pressed={mode === option.id} onClick={() => setMode(option.id)}>
                {option.label}
              </button>
            ))}
          </div>
          <p className="quiet" style={{ marginTop: 14 }}>
            {mode === "comparar"
              ? "Arrastra la línea del mapa para pasar de la imagen de antes a la de después."
              : mode === "cambio"
                ? "Rojo: la superficie se oscureció. Azul: se aclaró. Transparente: sin cambio."
                : "Imagen de radar en escala de grises: oscuro refleja poco (agua), claro refleja mucho."}
          </p>
          <label className="check" style={{ marginTop: 16 }}>
            <input type="checkbox" checked={showPolygons} onChange={(event) => setShowPolygons(event.target.checked)} />
            Mostrar las áreas detectadas
          </label>
        </div>

        <div className="block">
          <h2>Qué tipo de cambio</h2>
          {(insights.data?.by_type ?? []).map((row) => {
            const style = typeStyle(row.change_type);
            const on = !hidden.includes(row.change_type);
            return (
              <button
                key={row.change_type}
                className="typerow"
                aria-pressed={on}
                title={on ? "Ocultar en el mapa" : "Mostrar en el mapa"}
                onClick={() =>
                  setHidden((current) =>
                    on ? [...current, row.change_type] : current.filter((type) => type !== row.change_type),
                  )
                }
              >
                <span className="swatch" style={{ background: style.color }} />
                <span>{style.label}</span>
                <span className="num">{area(row.area_km2)}</span>
                <span className="meter">
                  <i style={{ width: `${(row.area_km2 / largestType) * 100}%`, background: style.color }} />
                </span>
              </button>
            );
          })}
          <p className="label" style={{ marginTop: 14 }}>
            Son hipótesis a partir de la señal del radar y de los eventos cercanos, no clasificaciones validadas.
          </p>
        </div>

        <div className="block">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 10 }}>
            <h2 style={{ margin: 0, fontSize: 15, fontWeight: 500 }}>Áreas {order === "area" ? "más grandes" : "más intensas"}</h2>
            <button className="btn tonal small" onClick={() => setOrder(order === "area" ? "score" : "area")}>
              {order === "area" ? "Ver las más intensas" : "Ver las más grandes"}
            </button>
          </div>
          {shown.length === 0 ? <p className="quiet">Activa algún tipo de cambio para ver sus áreas.</p> : null}
          {list.isLoading ? <p className="quiet">Cargando áreas…</p> : null}
          {(list.data?.items ?? []).map((change) => (
            <button
              key={change.id}
              className="changerow"
              aria-current={selected === change.id}
              onClick={() => {
                pick(change.id);
                setFocus(geometryBounds(change.geometry));
              }}
            >
              <span className="dot" style={{ background: typeStyle(change.change_type).color }} />
              <span>
                {area(change.area_km2)}
                <span className="quiet"> {typeStyle(change.change_type).label.replace("Posible ", "")}</span>
              </span>
              <span className="num" style={{ color: change.direction === "DECREASE" ? "var(--color-darker)" : "var(--color-brighter)" }}>
                {signedDb(change.mean_change_db)}
              </span>
            </button>
          ))}
          {list.data && list.data.total > list.data.items.length ? (
            <p className="label" style={{ marginTop: 12 }}>
              Se listan {list.data.items.length} de {number(list.data.total, 0)}. El resto está en el mapa: haz clic en cualquier área.
            </p>
          ) : null}
        </div>

        {warnings.length > 0 || sources.length > 0 || (totals?.aoi_coverage_percentage ?? 100) < 60 ? (
          <div className="block">
            <h2>Antes de sacar conclusiones</h2>
            <div style={{ display: "grid", gap: 8 }}>
              {(totals?.aoi_coverage_percentage ?? 100) < 60 ? (
                <p className="notice">
                  El radar solo cubrió el {number(totals?.aoi_coverage_percentage, 0)} % de la zona; fuera de esa franja puede haber cambios que no se ven.
                </p>
              ) : null}
              {sources.map(([name, info]) => (
                <p key={name} className="notice">
                  {name === "FIRMS" ? "Incendios" : name === "USGS" ? "Sismos" : "Lluvia"} sin consultar:{" "}
                  {info.status === "skipped" ? "falta configurar la clave de acceso." : "la fuente no respondió."}
                </p>
              ))}
              {warnings.map((warning, index) => (
                <p key={index} className="notice">{coded("job.warning", warning)}</p>
              ))}
            </div>
          </div>
        ) : null}
      </aside>

      <div className="stage">
        {tiles.data && before && after ? (
          <CompareMap
            jobId={id}
            tiles={tiles.data}
            mode={mode}
            showPolygons={showPolygons}
            hiddenTypes={hidden}
            selectedId={selected}
            onSelect={pick}
            focus={focus}
            beforeLabel={shortDate(before)}
            afterLabel={shortDate(after)}
          />
        ) : (
          <div className="compare" style={{ display: "grid", placeItems: "center" }}>
            <p className="quiet">{tiles.isError ? "No se pudieron cargar las imágenes de este análisis." : "Cargando el mapa…"}</p>
          </div>
        )}
        {before && after ? (
          <IntervalStrip before={before} after={after} rain={insights.data?.precipitation[0]} timeline={timeline.data} />
        ) : null}
      </div>

      {selected ? <ChangePanel changeId={selected} onClose={() => setSelected(null)} onLocate={setFocus} /> : null}
    </div>
  );
}
