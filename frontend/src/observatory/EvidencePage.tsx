import { useQuery } from "@tanstack/react-query";
import { Activity, CloudRain, Flame, Satellite } from "lucide-react";
import type { JSX } from "react";
import { Link, useParams } from "react-router-dom";

import { coded, sourceName, t, useT } from "@/i18n";
import { Rich } from "@/i18n/Rich";
import { area, db, number, shortDate, signedDb, typeStyle } from "@/observatory/lib";
import { interpretationService } from "@/services/interpretation.service";
import { useInterface } from "@/stores/interface";
import type { EvidenceRecord } from "@/types/evidence";

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

function EvidenceCard({ record }: { record: EvidenceRecord }) {
  const event = record.event;
  if (!event) return null;
  const meta = (event.metadata ?? {}) as Record<string, unknown>;
  const where =
    record.spatial_relation === "INTERSECTS"
      ? t("evidence.where.inside")
      : t("evidence.where.distance", { km: number(record.distance_km, 1) });

  let title = t("evidence.quake", { magnitude: number(event.magnitude, 1) });
  let detail = `${shortDate(event.event_date, true)}, ${where}.`;
  if (event.event_type === "FIRE") {
    title = t("evidence.fire");
    detail = `${shortDate(event.event_date, true)}, ${where}${
      event.magnitude != null ? `, ${number(event.magnitude, 1)} MW` : ""
    }.`;
  } else if (event.event_type === "PRECIPITATION") {
    const anomaly = typeof meta.anomaly_pct === "number" ? meta.anomaly_pct : null;
    title = t("evidence.rain_total", { mm: number(event.magnitude, 0) });
    detail = `${t("evidence.window", {
      from: shortDate(String(meta.window_start ?? "")),
      to: shortDate(String(meta.window_end ?? "")),
    })}${anomaly != null ? `, ${t("evidence.anomaly", { pct: `${anomaly >= 0 ? "+" : "−"}${number(Math.abs(anomaly), 0)}` })}` : ""}.`;
  }
  const color = SOURCE_COLOR[event.source] ?? "#555555";
  const glyph = SOURCE_GLYPH[event.source] ?? <Activity size={16} />;
  const lead = record.time_difference_hours != null
    ? ` ${t("evidence.lead", { hours: number(Math.abs(record.time_difference_hours), 0) })}`
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
  const t = useT();
  const scientific = useInterface((state) => state.scientific);
  const result = useQuery({
    queryKey: ["interpretation", changeId],
    queryFn: () => interpretationService.forChange(changeId),
  });

  if (result.isLoading) {
    return (
      <div className="page">
        <div className="inner quiet">{t("evidence.page.loading")}</div>
      </div>
    );
  }

  if (result.isError || !result.data) {
    return (
      <div className="page">
        <div className="inner">
          <p className="notice problem">{t("evidence.page.error")}</p>
          <Link className="btn tonal" style={{ marginTop: 16 }} to={`/analisis/${id}`}>
            {t("evidence.page.back")}
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
          {t("evidence.page.kicker")} · {t("home.range", { from: shortDate(item.period.before), to: shortDate(item.period.after, true) })}
        </p>
        <h1 className="title">{item.location?.name ?? t("value.no_region")}</h1>
        <p className="quiet" style={{ marginTop: 10 }}>
          {t("evidence.page.summary_area", { area: area(item.change.area_km2) })}{" "}
          <span className="num">{signedDb(item.change.mean_change_db)}</span>{" "}
          {t(darker ? "evidence.page.summary_darker" : "evidence.page.summary_brighter")}
        </p>

        <div className="verdict" style={{ borderColor: type.color }}>
          <p className="label">{t("evidence.page.suggests")}</p>
          <h2 style={{ color: type.color }}>{type.label}</h2>
          <p className="quiet" style={{ marginTop: 8 }}>
            {t(`evidence.confidence.${confidence}`, null, t("evidence.confidence.NONE"))}. {t("evidence.page.tentative")}
          </p>
          {item.classification.reasons.length > 0 ? (
            <ul className="steps-list" style={{ marginTop: 14 }}>
              {item.classification.reasons.map((reason, index) => (
                <li key={index}>{coded("reason", reason, "")}</li>
              ))}
            </ul>
          ) : (
            <p className="quiet" style={{ marginTop: 14 }}>
              {t("evidence.page.no_rule")}
            </p>
          )}
        </div>

        <section className="block" aria-labelledby="fuentes">
          <h2 id="fuentes">{t("evidence.page.sources")}</h2>
          <div className="sources">
            {sources.map(([name, state]) => (
              <div key={name} className="source" data-state={state.status}>
                <span className="glyph" style={{ color: SOURCE_COLOR[name] ?? "#555555" }} aria-hidden="true">
                  {SOURCE_GLYPH[name] ?? <Activity size={16} />}
                </span>
                <div>
                  <p style={{ fontWeight: 500 }}>{sourceName(name)}</p>
                  <p className="label">{t(`evidence.source_state.${state.status}`, null, state.status)}</p>
                  {state.status === "AVAILABLE" && state.events_found != null ? (
                    <p className="quiet">
                      {t(state.events_found === 1 ? "evidence.page.events_one" : "evidence.page.events", { count: number(state.events_found, 0) })}
                    </p>
                  ) : null}
                  {state.code ? <p className="quiet">{coded("limitation", { code: state.code, params: { source: name } })}</p> : null}
                  {scientific && state.detail ? <p className="quiet num">{state.detail}</p> : null}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="block" aria-labelledby="evidencia">
          <h2 id="evidencia">{t("evidence.page.linked")}</h2>
          {item.evidence.length === 0 ? (
            <p className="quiet" style={{ marginTop: 10 }}>
              {t("evidence.page.linked_none")}
            </p>
          ) : (
            item.evidence.map((record) => <EvidenceCard key={record.id} record={record} />)
          )}
          <p className="label" style={{ marginTop: 14 }}>
            {t("evidence.page.linked_note")}
          </p>
        </section>

        <section className="block" aria-labelledby="medidas">
          <h2 id="medidas">{t("evidence.page.data")}</h2>
          <dl className="facts">
            <div>
              <dt>{t("analysis.fact.area")}</dt>
              <dd className="num">{area(item.change.area_km2)}</dd>
            </div>
            <div>
              <dt>{t("evidence.page.mean_change")}</dt>
              <dd className="num">{signedDb(item.change.mean_change_db)}</dd>
            </div>
            <div>
              <dt>{t("analysis.fact.score")}</dt>
              <dd className="num">{number(item.change.change_score, 2)}</dd>
            </div>
            <div>
              <dt>{t("metric.valid_pixel_percentage")}</dt>
              <dd className="num">{item.change.valid_pixel_percentage != null ? `${number(item.change.valid_pixel_percentage, 1)} %` : t("value.no_data")}</dd>
            </div>
            <div>
              <dt>{t("analysis.fact.interval")}</dt>
              <dd className="num">{item.period.interval_days != null ? `${number(item.period.interval_days, 0)} ${t("home.unit.days")}` : t("value.no_data")}</dd>
            </div>
            <div>
              <dt>{t("analysis.fact.product")}</dt>
              <dd>{item.observation.product_type ?? t("value.no_data")}</dd>
            </div>
          </dl>

          {scientific ? (
            <>
              <h3 style={{ marginTop: 24 }}>{t("evidence.page.technical")}</h3>
              <dl className="facts">
                <div>
                  <dt>{t("analysis.fact.maturity")}</dt>
                  <dd className="num">{item.observation.maturity ?? t("value.no_data")}</dd>
                </div>
                <div>
                  <dt>{t("analysis.fact.polarization")}</dt>
                  <dd className="num">{item.observation.polarization?.join(" · ") ?? t("value.no_data")}</dd>
                </div>
                <div>
                  <dt>{t("analysis.fact.orbit")}</dt>
                  <dd className="num">{item.observation.orbit_direction ?? t("value.no_data")}</dd>
                </div>
                <div>
                  <dt>{t("analysis.fact.version")}</dt>
                  <dd className="num">{item.observation.processing_version ?? t("value.no_data")}</dd>
                </div>
                <div>
                  <dt>{t("analysis.fact.product")}</dt>
                  <dd className="num" style={{ fontSize: 12 }}>{item.observation.product_id ?? t("value.no_data")}</dd>
                </div>
                <div>
                  <dt>{t("metric.detection_threshold_db")}</dt>
                  <dd className="num">
                    {db(item.metrics.find((metric) => metric.name === "detection_threshold_db")?.value ?? null)}
                  </dd>
                </div>
              </dl>
            </>
          ) : null}
        </section>

        <section className="block" aria-labelledby="conclusion">
          <h2 id="conclusion">{t("evidence.page.conclude")}</h2>
          <ul className="steps-list">
            <li>
              <Rich
                text={t(darker ? "evidence.conclude.observed_down" : "evidence.conclude.observed_up", {
                  from: shortDate(item.period.before),
                  to: shortDate(item.period.after, true),
                  db: number(Math.abs(item.change.mean_change_db ?? 0), 1),
                  area: area(item.change.area_km2),
                })}
              />
            </li>
            <li>
              <Rich
                text={
                  item.evidence.length > 0
                    ? t(item.evidence.length === 1 ? "evidence.conclude.extra_one" : "evidence.conclude.extra", {
                        count: item.evidence.length,
                      })
                    : t("evidence.conclude.extra_none")
                }
              />
            </li>
            <li>
              <Rich
                text={
                  unclassified
                    ? t("evidence.conclude.related_none")
                    : t("evidence.conclude.related", { type: type.label.toLowerCase() })
                }
              />
            </li>
            <li>
              <Rich
                text={
                  missing.length > 0
                    ? t("evidence.conclude.missing", { sources: missing.map(sourceName).join(", ") })
                    : t("evidence.conclude.missing_none")
                }
              />
            </li>
            <li>
              <Rich text={t("evidence.conclude.cannot")} />
            </li>
          </ul>
        </section>

        <section className="block" aria-labelledby="limites">
          <h2 id="limites">{t("evidence.page.limits")}</h2>
          <ul className="steps-list">
            {item.limitations.map((limitation, index) => (
              <li key={index}>
                <Rich text={coded("limitation", limitation)} />
              </li>
            ))}
          </ul>
          <p style={{ marginTop: 20, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link className="btn tonal" to={`/analisis/${item.job_id}`}>
              {t("evidence.page.back")}
            </Link>
            <Link className="btn tonal" to="/metodologia">
              {t("evidence.page.how")}
            </Link>
          </p>
        </section>
      </div>
    </div>
  );
}
