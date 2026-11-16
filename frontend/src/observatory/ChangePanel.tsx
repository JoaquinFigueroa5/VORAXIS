import { useQuery } from "@tanstack/react-query";
import { CloudRain, Flame, Activity, X } from "lucide-react";
import { Link } from "react-router-dom";

import { t, useT } from "@/i18n";
import { area, db, geometryBounds, number, shortDate, signedDb, typeStyle, type Bounds } from "@/observatory/lib";
import { changesService } from "@/services/changes.service";
import { evidenceService } from "@/services/evidence.service";
import type { EvidenceRecord } from "@/types/evidence";

const SCALE_MIN = -30;
const SCALE_MAX = 0;

function onScale(value: number): number {
  return ((Math.min(SCALE_MAX, Math.max(SCALE_MIN, value)) - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)) * 100;
}

/** Labels near either end of the scale hang inwards so they never clip. */
function edge(value: number): string {
  const at = onScale(value);
  return at > 72 ? " edge-right" : at < 28 ? " edge-left" : "";
}

function EvidenceRow({ record }: { record: EvidenceRecord }) {
  const event = record.event;
  if (!event) return null;
  const meta = (event.metadata ?? {}) as Record<string, unknown>;
  const where =
    record.spatial_relation === "INTERSECTS"
      ? t("evidence.where.inside")
      : t("evidence.where.distance", { km: number(record.distance_km, 1) });

  let glyph = <Activity size={16} />;
  let color = "#b0305c";
  let title = t("evidence.quake", { magnitude: number(event.magnitude, 1) });
  let detail = `${shortDate(event.event_date, true)}, ${where}.`;

  if (event.event_type === "FIRE") {
    glyph = <Flame size={16} />;
    color = "#d2571b";
    title = t("evidence.fire");
    detail = `${shortDate(event.event_date, true)}, ${where}${
      event.magnitude != null ? `, ${number(event.magnitude, 1)} MW` : ""
    }.`;
  } else if (event.event_type === "PRECIPITATION") {
    glyph = <CloudRain size={16} />;
    color = "#1f6fb2";
    const anomaly = typeof meta.anomaly_pct === "number" ? meta.anomaly_pct : null;
    title = t("evidence.rain", { mm: number(event.magnitude, 0) });
    detail = `${t("evidence.window", {
      from: shortDate(String(meta.window_start ?? "")),
      to: shortDate(String(meta.window_end ?? "")),
    })}${anomaly != null ? `, ${t("evidence.anomaly", { pct: `${anomaly >= 0 ? "+" : "−"}${number(Math.abs(anomaly), 0)}` })}` : ""}.`;
  }

  return (
    <div className="evidence">
      <span className="glyph" style={{ color }} aria-hidden="true">
        {glyph}
      </span>
      <div>
        <p style={{ fontWeight: 500 }}>{title}</p>
        <p className="quiet">{detail}</p>
      </div>
    </div>
  );
}

interface ChangePanelProps {
  changeId: string;
  onClose: () => void;
  onLocate: (bounds: Bounds) => void;
}

export function ChangePanel({ changeId, onClose, onLocate }: ChangePanelProps) {
  const t = useT();
  const change = useQuery({ queryKey: ["change", changeId], queryFn: () => changesService.get(changeId) });
  const metrics = useQuery({ queryKey: ["change", changeId, "metrics"], queryFn: () => changesService.metrics(changeId) });
  const evidence = useQuery({ queryKey: ["change", changeId, "evidence"], queryFn: () => evidenceService.forChange(changeId) });

  if (change.isLoading) {
    return (
      <aside className="detail">
        <div className="block quiet">{t("panel.loading")}</div>
      </aside>
    );
  }
  if (change.isError || !change.data) {
    return (
      <aside className="detail">
        <div className="block">
          <p className="notice problem">{t("panel.error")}</p>
        </div>
      </aside>
    );
  }

  const item = change.data;
  const type = typeStyle(item.change_type);
  const value = (name: string) => metrics.data?.find((metric) => metric.metric_name === name)?.value ?? null;
  const beforeDb = value("mean_backscatter_before_db");
  const afterDb = value("mean_backscatter_after_db");
  const threshold = value("detection_threshold_db");
  const darker = item.direction === "DECREASE";
  const records = evidence.data ?? [];

  return (
    <aside className="detail" aria-label={t("panel.aria")}>
      <div className="block">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <span className="chip">
            <i style={{ background: type.color }} />
            {area(item.area_km2)}
          </span>
          <button className="btn tonal small icon" onClick={onClose} aria-label={t("panel.close")}>
            <X size={16} />
          </button>
        </div>
        <h2 className="title" style={{ margin: "16px 0 10px" }}>
          {type.label}
        </h2>
        <p className="quiet">{type.reading}</p>
        <button className="btn tonal small" style={{ marginTop: 16 }} onClick={() => onLocate(geometryBounds(item.geometry))}>
          {t("panel.locate")}
        </button>
        <Link className="btn small" style={{ marginTop: 8 }} to={`/analisis/${item.job_id}/evidencia/${item.id}`}>
          {t("panel.explain")}
        </Link>
      </div>

      <div className="block">
        <p className="figure" style={{ color: darker ? "var(--color-darker)" : "var(--color-brighter)" }}>
          {signedDb(item.mean_change_db)}
        </p>
        <p className="quiet" style={{ marginTop: 10 }}>
          {t(darker ? "panel.signal.down" : "panel.signal.up")}
          {threshold ? t("panel.signal.times", { times: number(Math.abs(item.mean_change_db ?? 0) / threshold, 1) }) : ""}.
        </p>

        {beforeDb != null && afterDb != null ? (
          <div className="dbscale" role="img" aria-label={t("panel.scale_aria", { before: db(beforeDb), after: db(afterDb) })}>
            <div className="track" />
            <div className={`pin before${edge(beforeDb)}`} style={{ left: `${onScale(beforeDb)}%` }}>
              <b>{t("downloads.before")} {db(beforeDb)}</b>
            </div>
            <div className={`pin after${edge(afterDb)}`} style={{ left: `${onScale(afterDb)}%` }}>
              <b>{t("downloads.after")} {db(afterDb)}</b>
            </div>
          </div>
        ) : null}
        <p className="label">{t("panel.scale_note")}</p>
      </div>

      <div className="block">
        <dl className="facts">
          <div>
            <dt>{t("panel.fact.label")}</dt>
            <dd>{t(item.change_type === "UNCLASSIFIED" ? "panel.fact.unclassified" : "panel.fact.tentative")}</dd>
          </div>
          <div>
            <dt>{t("analysis.fact.score")}</dt>
            <dd className="num">{number(item.change_score, 2)}</dd>
          </div>
          <div>
            <dt>{t("metric.detection_threshold_db")}</dt>
            <dd className="num">{db(threshold)}</dd>
          </div>
          <div>
            <dt>{t("panel.fact.peak")}</dt>
            <dd className="num">{signedDb(value("peak_change_db"))}</dd>
          </div>
        </dl>
      </div>

      <div className="block">
        <h3>{t("panel.nearby.title")}</h3>
        {evidence.isLoading ? <p className="quiet">{t("panel.nearby.loading")}</p> : null}
        {!evidence.isLoading && records.length === 0 ? (
          <p className="quiet">{t("panel.nearby.none")}</p>
        ) : null}
        {records.slice(0, 8).map((record) => (
          <EvidenceRow key={record.id} record={record} />
        ))}
        <p className="label" style={{ marginTop: 14 }}>
          {t("panel.nearby.note")}
        </p>
      </div>
    </aside>
  );
}
