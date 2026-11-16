import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { useT } from "@/i18n";
import { Rich } from "@/i18n/Rich";
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
  const t = useT();
  const insights = useQuery({ queryKey: ["insights"], queryFn: () => insightsService.summary() });

  if (insights.isLoading) {
    return (
      <div className="page">
        <div className="inner quiet">{t("insights.loading")}</div>
      </div>
    );
  }

  if (insights.isError || !insights.data) {
    return (
      <div className="page">
        <div className="inner">
          <p className="notice problem">{t("insights.error")}</p>
          <button className="btn tonal" style={{ marginTop: 16 }} onClick={() => insights.refetch()}>
            {t("action.retry")}
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
        <p className="label">{t("insights.kicker")}</p>
        <h1 className="title">{t("insights.title")}</h1>
        <p className="quiet" style={{ marginTop: 12 }}>
          {t("insights.lead")}
        </p>

        <dl className="facts wide" style={{ marginTop: 28 }}>
          <div>
            <dt>{t("insights.fact.locations")}</dt>
            <dd className="num">{number(data.locations, 0)}</dd>
          </div>
          <div>
            <dt>{t("insights.fact.scenes")}</dt>
            <dd className="num">{number(data.scenes, 0)}</dd>
          </div>
          <div>
            <dt>{t("insights.fact.observations")}</dt>
            <dd className="num">{number(data.observations, 0)}</dd>
          </div>
          <div>
            <dt>{t("insights.fact.completed")}</dt>
            <dd className="num">
              {number(completed, 0)}
              <span className="quiet"> {t("insights.of", { total: number(analyses, 0) })}</span>
            </dd>
          </div>
          <div>
            <dt>{t("home.stat.changes")}</dt>
            <dd className="num">{number(data.change_events, 0)}</dd>
          </div>
          <div>
            <dt>{t("insights.fact.area")}</dt>
            <dd className="num">{area(data.change_area_km2)}</dd>
          </div>
          <div>
            <dt>{t("insights.fact.evidence")}</dt>
            <dd className="num">{number(data.evidence_records, 0)}</dd>
          </div>
          <div>
            <dt>{t("insights.fact.events")}</dt>
            <dd className="num">{number(data.auxiliary_events, 0)}</dd>
          </div>
        </dl>

        {!enough ? (
          <div className="block" style={{ marginTop: 32 }}>
            <h2>{t("insights.thin.title")}</h2>
            <p className="quiet" style={{ marginTop: 10 }}>
              {t(completed === 1 ? "insights.thin.body_one" : "insights.thin.body", {
                count: number(completed, 0),
                min: MIN_ANALYSES,
              })}
            </p>
            <Link className="btn tonal" style={{ marginTop: 16 }} to="/nuevo">
              {t("insights.thin.cta")}
            </Link>
          </div>
        ) : (
          <>
            <section className="block" aria-labelledby="por-tipo">
              <h2 id="por-tipo">{t("insights.type.title")}</h2>
              <p className="quiet" style={{ marginTop: 8 }}>
                <Rich text={t("insights.type.note")} />
              </p>
              <Bars
                rows={data.by_type.map((row) => ({
                  key: row.change_type,
                  label: typeStyle(row.change_type).label,
                  value: row.count,
                  note: `${number(row.count, 0)} · ${area(row.area_km2)}`,
                  color: typeStyle(row.change_type).color,
                }))}
              />
            </section>

            <section className="block" aria-labelledby="por-direccion">
              <h2 id="por-direccion">{t("insights.direction.title")}</h2>
              <p className="quiet" style={{ marginTop: 8 }}>
                {t("insights.direction.note")}
              </p>
              <Bars
                rows={data.by_direction.map((row) => ({
                  key: row.direction ?? "unknown",
                  label: t(row.direction === "DECREASE" ? "insights.direction.darker" : row.direction === "INCREASE" ? "insights.direction.brighter" : "insights.direction.none"),
                  value: row.count,
                  note: `${number(row.count, 0)} · ${area(row.area_km2)}`,
                  color: row.direction === "DECREASE" ? "var(--color-darker)" : "var(--color-brighter)",
                }))}
              />
            </section>

            {data.by_month.length > 1 ? (
              <section className="block" aria-labelledby="por-mes">
                <h2 id="por-mes">{t("insights.month.title")}</h2>
                <p className="quiet" style={{ marginTop: 8 }}>
                  {t("insights.month.note")}
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
              <h2 id="por-region">{t("insights.region.title")}</h2>
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
