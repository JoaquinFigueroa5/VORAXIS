import { useQuery } from "@tanstack/react-query";
import { Activity, CloudRain, Flame, Satellite } from "lucide-react";
import type { JSX } from "react";
import { Link, useParams } from "react-router-dom";

import { area, db, number, shortDate, signedDb, typeStyle } from "@/observatory/lib";
import { interpretationService } from "@/services/interpretation.service";
import { useInterface } from "@/stores/interface";
import type { EvidenceRecord } from "@/types/evidence";
import type { SourceStatus } from "@/types/interpretation";

const SOURCE_GLYPH: Record<string, JSX.Element> = {
  NISAR: <Satellite size={16} />,
  USGS: <Activity size={16} />,
  FIRMS: <Flame size={16} />,
  POWER: <CloudRain size={16} />,
};

const SOURCE_COLOR: Record<string, string> = {
  NISAR: "#232323",
  USGS: "#b0305c",
  FIRMS: "#d2571b",
  POWER: "#1f6fb2",
};

const SOURCE_STATE: Record<SourceStatus, string> = {
  AVAILABLE: "Consultada",
  UNAVAILABLE: "No respondió",
  NOT_CONFIGURED: "No configurada",
};

const CONFIDENCE: Record<string, string> = {
  MEDIUM: "Evidencia parcial",
  LOW: "Evidencia débil",
  NONE: "Sin evidencia suficiente",
};

function EvidenceCard({ record }: { record: EvidenceRecord }) {
  const event = record.event;
  if (!event) return null;
  const meta = (event.metadata ?? {}) as Record<string, unknown>;
  const where = record.spatial_relation === "INTERSECTS" ? "dentro del área" : `a ${number(record.distance_km, 1)} km`;

  let title = `Sismo M${number(event.magnitude, 1)}`;
  let detail = `${shortDate(event.event_date, true)}, ${where}.`;
  if (event.event_type === "FIRE") {
    title = "Foco de fuego activo";
    detail = `${shortDate(event.event_date, true)}, ${where}${
      event.magnitude != null ? `, ${number(event.magnitude, 1)} MW` : ""
    }.`;
  } else if (event.event_type === "PRECIPITATION") {
    const anomaly = typeof meta.anomaly_pct === "number" ? meta.anomaly_pct : null;
    title = `${number(event.magnitude, 0)} mm de lluvia acumulada`;
    detail = `Del ${shortDate(String(meta.window_start ?? ""))} al ${shortDate(String(meta.window_end ?? ""))}${
      anomaly != null ? `, ${anomaly >= 0 ? "+" : "−"}${number(Math.abs(anomaly), 0)} % frente a lo normal` : ""
    }.`;
  }
  const color = SOURCE_COLOR[event.source] ?? "#555555";
  const glyph = SOURCE_GLYPH[event.source] ?? <Activity size={16} />;
  // The engine's own explanation is English prose; the UI shows the same facts in Spanish.
  const lead = record.time_difference_hours != null
    ? ` ${number(Math.abs(record.time_difference_hours), 0)} h antes de la segunda pasada.`
    : "";

  return (
    <div className="evidence">
      <span className="glyph" style={{ color }} aria-hidden="true">
        {glyph}
      </span>
      <div>
        <p style={{ fontWeight: 500 }}>
          {title} <span className="label">{event.source}</span>
        </p>
        <p className="quiet">
          {detail}
          {lead}
        </p>
      </div>
    </div>
  );
}

export function EvidencePage() {
  const { id = "", changeId = "" } = useParams();
  const scientific = useInterface((state) => state.scientific);
  const result = useQuery({
    queryKey: ["interpretation", changeId],
    queryFn: () => interpretationService.forChange(changeId),
  });

  if (result.isLoading) {
    return (
      <div className="page">
        <div className="inner quiet">Reuniendo métricas y evidencia…</div>
      </div>
    );
  }

  if (result.isError || !result.data) {
    return (
      <div className="page">
        <div className="inner">
          <p className="notice problem">No se pudo cargar este cambio o ya no existe.</p>
          <Link className="btn tonal" style={{ marginTop: 16 }} to={`/analisis/${id}`}>
            Volver al análisis
          </Link>
        </div>
      </div>
    );
  }

  const item = result.data;
  const type = typeStyle(item.change.change_type);
  const unclassified = item.change.change_type === "UNCLASSIFIED";
  const sources = Object.entries(item.sources);
  const missing = sources.filter(([, state]) => state.status !== "AVAILABLE").map(([name]) => name);
  const confidence = item.classification.confidence ?? "NONE";
  const darker = item.change.direction === "DECREASE";

  return (
    <div className="page">
      <div className="inner wide">
        <p className="label">
          Evidence center · {shortDate(item.period.before)} a {shortDate(item.period.after, true)}
        </p>
        <h1 className="title">{item.location?.name ?? "Cambio sin región"}</h1>
        <p className="quiet" style={{ marginTop: 10 }}>
          {area(item.change.area_km2)} de cambio en la señal de radar.{" "}
          <span className="num">{signedDb(item.change.mean_change_db)}</span> en promedio,{" "}
          {darker ? "más oscuro" : "más brillante"} en la segunda fecha.
        </p>

        <div className="verdict" style={{ borderColor: type.color }}>
          <p className="label">Lo que sugiere la señal</p>
          <h2 style={{ color: type.color }}>{type.label}</h2>
          <p className="quiet" style={{ marginTop: 8 }}>
            {CONFIDENCE[confidence] ?? CONFIDENCE.NONE}. La clasificación es tentativa: describe lo que la firma del
            radar y los eventos cercanos hacen compatible, no lo que se ha confirmado.
          </p>
          {item.classification.reasons.length > 0 ? (
            <ul className="steps-list" style={{ marginTop: 14 }}>
              {item.classification.reasons.map((reason, index) => (
                <li key={index}>{reason}</li>
              ))}
            </ul>
          ) : (
            <p className="quiet" style={{ marginTop: 14 }}>
              No hay una regla que encaje con esta firma. Se deja sin clasificar en lugar de forzar una etiqueta.
            </p>
          )}
        </div>

        <section className="block" aria-labelledby="fuentes">
          <h2 id="fuentes">Qué se pudo consultar</h2>
          <div className="sources">
            {sources.map(([name, state]) => (
              <div key={name} className="source" data-state={state.status}>
                <span className="glyph" style={{ color: SOURCE_COLOR[name] ?? "#555555" }} aria-hidden="true">
                  {SOURCE_GLYPH[name] ?? <Activity size={16} />}
                </span>
                <div>
                  <p style={{ fontWeight: 500 }}>{name}</p>
                  <p className="label">{SOURCE_STATE[state.status]}</p>
                  {state.status === "AVAILABLE" && state.events_found != null ? (
                    <p className="quiet">
                      {number(state.events_found, 0)} {state.events_found === 1 ? "evento" : "eventos"} en la ventana
                    </p>
                  ) : null}
                  {state.detail ? <p className="quiet">{state.detail}</p> : null}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="block" aria-labelledby="evidencia">
          <h2 id="evidencia">Evidencia vinculada</h2>
          {item.evidence.length === 0 ? (
            <p className="quiet" style={{ marginTop: 10 }}>
              No se vinculó ningún evento a este polígono. Puede que no hubiera nada cerca o que las fuentes no
              respondieran: mira el estado de cada fuente arriba.
            </p>
          ) : (
            item.evidence.map((record) => <EvidenceCard key={record.id} record={record} />)
          )}
          <p className="label" style={{ marginTop: 14 }}>
            Cada vínculo guarda la distancia y la diferencia temporal. Coincidir no demuestra causar.
          </p>
        </section>

        <section className="block" aria-labelledby="medidas">
          <h2 id="medidas">Esto es lo que dicen los datos</h2>
          <dl className="facts">
            <div>
              <dt>Superficie afectada</dt>
              <dd className="num">{area(item.change.area_km2)}</dd>
            </div>
            <div>
              <dt>Cambio medio</dt>
              <dd className="num">{signedDb(item.change.mean_change_db)}</dd>
            </div>
            <div>
              <dt>Intensidad relativa</dt>
              <dd className="num">{number(item.change.change_score, 2)}</dd>
            </div>
            <div>
              <dt>Píxeles válidos</dt>
              <dd className="num">{item.change.valid_pixel_percentage != null ? `${number(item.change.valid_pixel_percentage, 1)} %` : "sin dato"}</dd>
            </div>
            <div>
              <dt>Intervalo</dt>
              <dd className="num">{item.period.interval_days != null ? `${number(item.period.interval_days, 0)} días` : "sin dato"}</dd>
            </div>
            <div>
              <dt>Producto</dt>
              <dd>{item.observation.product_type ?? "sin dato"}</dd>
            </div>
          </dl>

          {scientific ? (
            <>
              <h3 style={{ marginTop: 24 }}>Detalle técnico</h3>
              <dl className="facts">
                <div>
                  <dt>Madurez</dt>
                  <dd className="num">{item.observation.maturity ?? "sin dato"}</dd>
                </div>
                <div>
                  <dt>Polarización</dt>
                  <dd className="num">{item.observation.polarization?.join(" · ") ?? "sin dato"}</dd>
                </div>
                <div>
                  <dt>Órbita</dt>
                  <dd className="num">{item.observation.orbit_direction ?? "sin dato"}</dd>
                </div>
                <div>
                  <dt>Versión de proceso</dt>
                  <dd className="num">{item.observation.processing_version ?? "sin dato"}</dd>
                </div>
                <div>
                  <dt>Producto</dt>
                  <dd className="num" style={{ fontSize: 12 }}>{item.observation.product_id ?? "sin dato"}</dd>
                </div>
                <div>
                  <dt>Umbral de detección</dt>
                  <dd className="num">
                    {db(item.metrics.find((metric) => metric.name === "detection_threshold_db")?.value ?? null)}
                  </dd>
                </div>
              </dl>
            </>
          ) : null}
        </section>

        <section className="block" aria-labelledby="conclusion">
          <h2 id="conclusion">Qué podemos concluir</h2>
          <ul className="steps-list">
            <li>
              <strong>Qué se observó.</strong> Entre {shortDate(item.period.before)} y{" "}
              {shortDate(item.period.after, true)} la señal de radar {darker ? "bajó" : "subió"}{" "}
              {number(Math.abs(item.change.mean_change_db ?? 0), 1)} dB en {area(item.change.area_km2)}.
            </li>
            <li>
              <strong>Qué información adicional hay.</strong>{" "}
              {item.evidence.length > 0
                ? `Se vincularon ${item.evidence.length} ${item.evidence.length === 1 ? "evento" : "eventos"} de fuentes auxiliares en el intervalo.`
                : "No se vinculó ningún evento auxiliar en el intervalo."}
            </li>
            <li>
              <strong>Qué fenómeno podría estar relacionado.</strong>{" "}
              {unclassified
                ? "Ninguno identificable con estas reglas."
                : `La firma es compatible con ${type.label.toLowerCase()}.`}
            </li>
            <li>
              <strong>Qué falta.</strong>{" "}
              {missing.length > 0
                ? `Sin ${missing.join(", ")} el contexto está incompleto.`
                : "Todas las fuentes respondieron, pero la confirmación requiere datos hidrológicos, de cobertura o de campo."}
            </li>
            <li>
              <strong>Qué no se puede concluir.</strong> Que el cambio causara ese fenómeno, ni su magnitud en
              superficie: el radar mide retrodispersión, no profundidad de agua ni temperatura.
            </li>
          </ul>
        </section>

        <section className="block" aria-labelledby="limites">
          <h2 id="limites">Limitaciones de esta interpretación</h2>
          <ul className="steps-list">
            {item.limitations.map((limitation, index) => (
              <li key={index}>{limitation}</li>
            ))}
          </ul>
          <p style={{ marginTop: 20, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link className="btn tonal" to={`/analisis/${item.job_id}`}>
              Volver al análisis
            </Link>
            <Link className="btn tonal" to="/metodologia">
              Cómo se calcula
            </Link>
          </p>
        </section>
      </div>
    </div>
  );
}
