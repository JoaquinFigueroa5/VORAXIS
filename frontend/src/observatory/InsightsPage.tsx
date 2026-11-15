import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { area, number, shortDate, typeStyle } from "@/observatory/lib";
import { insightsService } from "@/services/insights.service";

/** Below this, a chart says more about the sample than about the planet. */
const MIN_ANALYSES = 3;

function Bars({
  rows,
}: {
  rows: { key: string; label: string; value: number; note: string; color: string }[];
}) {
  const largest = Math.max(...rows.map((row) => row.value), 1);
  return (
    <div className="distro">
      {rows.map((row) => (
        <div key={row.key} className="distro__row">
          <span className="distro__label">
            <i className="swatch" style={{ background: row.color }} />
            {row.label}
          </span>
          <span className="num">{row.note}</span>
          <span className="distro__meter">
            <i style={{ width: `${(row.value / largest) * 100}%`, background: row.color }} />
          </span>
        </div>
      ))}
    </div>
  );
}

export function InsightsPage() {
  const insights = useQuery({ queryKey: ["insights"], queryFn: () => insightsService.summary() });

  if (insights.isLoading) {
    return (
      <div className="page">
        <div className="inner quiet">Contando lo que hay…</div>
      </div>
    );
  }

  if (insights.isError || !insights.data) {
    return (
      <div className="page">
        <div className="inner">
          <p className="notice problem">No se pudieron cargar las estadísticas.</p>
          <button className="btn tonal" style={{ marginTop: 16 }} onClick={() => insights.refetch()}>
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const data = insights.data;
  const analyses = Object.values(data.jobs).reduce((sum, count) => sum + count, 0);
  const completed = data.jobs.COMPLETED ?? 0;
  const enough = completed >= MIN_ANALYSES && data.by_type.length > 0;

  return (
    <div className="page">
      <div className="inner wide">
        <p className="label">Global insights</p>
        <h1 className="title">Qué se ha encontrado hasta ahora</h1>
        <p className="quiet" style={{ marginTop: 12 }}>
          Todas las cifras salen de los análisis guardados en este servidor. No se proyectan ni se estiman valores
          ausentes.
        </p>

        <dl className="facts wide" style={{ marginTop: 28 }}>
          <div>
            <dt>Regiones registradas</dt>
            <dd className="num">{number(data.locations, 0)}</dd>
          </div>
          <div>
            <dt>Escenas NISAR en catálogo</dt>
            <dd className="num">{number(data.scenes, 0)}</dd>
          </div>
          <div>
            <dt>Observaciones listas</dt>
            <dd className="num">{number(data.observations, 0)}</dd>
          </div>
          <div>
            <dt>Análisis completados</dt>
            <dd className="num">
              {number(completed, 0)}
              <span className="quiet"> de {number(analyses, 0)}</span>
            </dd>
          </div>
          <div>
            <dt>Cambios detectados</dt>
            <dd className="num">{number(data.change_events, 0)}</dd>
          </div>
          <div>
            <dt>Área con cambios</dt>
            <dd className="num">{area(data.change_area_km2)}</dd>
          </div>
          <div>
            <dt>Evidencias vinculadas</dt>
            <dd className="num">{number(data.evidence_records, 0)}</dd>
          </div>
          <div>
            <dt>Eventos auxiliares guardados</dt>
            <dd className="num">{number(data.auxiliary_events, 0)}</dd>
          </div>
        </dl>

        {!enough ? (
          <div className="block" style={{ marginTop: 32 }}>
            <h2>Datos insuficientes para tendencias</h2>
            <p className="quiet" style={{ marginTop: 10 }}>
              Hay {number(completed, 0)} {completed === 1 ? "análisis completado" : "análisis completados"}. Con menos
              de {MIN_ANALYSES} cualquier distribución describiría el puñado de zonas elegidas, no el planeta. Cuando
              haya más, aquí aparecerán las gráficas.
            </p>
            <Link className="btn tonal" style={{ marginTop: 16 }} to="/nuevo">
              Crear otro análisis
            </Link>
          </div>
        ) : (
          <>
            <section className="block" aria-labelledby="por-tipo">
              <h2 id="por-tipo">Cambios por clasificación</h2>
              <p className="quiet" style={{ marginTop: 8 }}>
                Las etiquetas <span className="num">POSSIBLE_*</span> son hipótesis del clasificador, no diagnósticos.
              </p>
              <Bars
                rows={data.by_type.map((row) => ({
                  key: row.change_type,
                  label: row.label,
                  value: row.count,
                  note: `${number(row.count, 0)} · ${area(row.area_km2)}`,
                  color: typeStyle(row.change_type).color,
                }))}
              />
            </section>

            <section className="block" aria-labelledby="por-direccion">
              <h2 id="por-direccion">Dirección de la señal</h2>
              <p className="quiet" style={{ marginTop: 8 }}>
                Oscurecimiento: la superficie devolvió menos señal (agua, suelo liso). Aclaramiento: devolvió más
                (estructuras, rebote doble).
              </p>
              <Bars
                rows={data.by_direction.map((row) => ({
                  key: row.direction ?? "unknown",
                  label: row.direction === "DECREASE" ? "Se oscureció" : row.direction === "INCREASE" ? "Se aclaró" : "Sin dirección",
                  value: row.count,
                  note: `${number(row.count, 0)} · ${area(row.area_km2)}`,
                  color: row.direction === "DECREASE" ? "var(--color-darker)" : "var(--color-brighter)",
                }))}
              />
            </section>

            {data.by_month.length > 1 ? (
              <section className="block" aria-labelledby="por-mes">
                <h2 id="por-mes">Por mes de análisis</h2>
                <p className="quiet" style={{ marginTop: 8 }}>
                  Fecha en que se procesó el análisis, no la fecha de la observación.
                </p>
                <Bars
                  rows={data.by_month.map((row) => ({
                    key: row.month,
                    label: shortDate(`${row.month}-01`, true),
                    value: row.count,
                    note: `${number(row.count, 0)} · ${area(row.area_km2)}`,
                    color: "var(--color-ink)",
                  }))}
                />
              </section>
            ) : null}

            <section className="block" aria-labelledby="por-region">
              <h2 id="por-region">Por región</h2>
              <Bars
                rows={data.by_location.map((row) => ({
                  key: row.location_id,
                  label: row.name,
                  value: row.count,
                  note: `${number(row.count, 0)} · ${area(row.area_km2)}`,
                  color: "var(--color-ink)",
                }))}
              />
            </section>
          </>
        )}
      </div>
    </div>
  );
}
