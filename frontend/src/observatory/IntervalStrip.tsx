import { useT } from "@/i18n";
import { addDays, isoDay, number, shortDate } from "@/observatory/lib";
import type { JobInsights } from "@/types/analysis";
import type { TimelineContext } from "@/types/context";

interface IntervalStripProps {
  before: string;
  after: string;
  rain: JobInsights["precipitation"][number] | undefined;
  timeline: TimelineContext | undefined;
}

/**
 * The days between the two radar passes, plus the week before the first one.
 * The radar only sees the two ends; this strip shows what happened in between.
 */
export function IntervalStrip({ before, after, rain, timeline }: IntervalStripProps) {
  const t = useT();
  const first = isoDay(before);
  const last = isoDay(after);
  const start = rain?.series[0]?.date ?? addDays(first, -7);

  const days: string[] = [];
  for (let day = start; day <= last && days.length < 90; day = addDays(day, 1)) days.push(day);

  const mm = new Map((rain?.series ?? []).map((point) => [point.date, point.mm ?? 0]));
  const peak = Math.max(1, ...mm.values());
  const fires = new Map<string, number>();
  const quakes = new Map<string, number>();
  for (const event of timeline?.events ?? []) {
    const day = isoDay(event.date);
    if (event.kind === "fire") fires.set(day, (fires.get(day) ?? 0) + (event.detections ?? 1));
    if (event.kind === "earthquake") quakes.set(day, Math.max(quakes.get(day) ?? 0, event.magnitude ?? 0));
  }
  const fireDays = [...fires.values()].length;
  const fireTotal = [...fires.values()].reduce((sum, count) => sum + count, 0);
  const strongest = Math.max(0, ...quakes.values());

  return (
    <section className="interval" aria-label={t("strip.aria")}>
      <div className="head">
        <h2>{t("strip.title")}</h2>
        {rain?.total_mm != null ? (
          <p className="quiet">
            {t("strip.rained")} <strong className="num" style={{ color: "var(--color-ink)" }}>{number(rain.total_mm, 0)} mm</strong>
            {rain.anomaly_pct != null
              ? `, ${t("evidence.anomaly", { pct: `${rain.anomaly_pct >= 0 ? "+" : "−"}${number(Math.abs(rain.anomaly_pct), 0)}` })}`
              : ""}
            .
          </p>
        ) : (
          <p className="quiet">{t("strip.no_rain")}</p>
        )}
        <p className="quiet">
          {fireTotal > 0
            ? t(fireDays === 1 ? "strip.fires_one_day" : "strip.fires", { count: fireTotal, days: fireDays })
            : t("strip.no_fires")}{" "}
          {strongest > 0 ? t("strip.quake", { magnitude: number(strongest, 1) }) : t("strip.no_quakes")}
        </p>
      </div>

      <div className="days" role="img" aria-label={t("strip.days_aria", { from: shortDate(start), to: shortDate(last) })}>
        {days.map((day) => {
          const value = mm.get(day) ?? 0;
          const pass = day === first || day === last;
          const title = `${shortDate(day)}: ${number(value, 0)} mm${fires.has(day) ? `, ${t("strip.day_fires", { count: fires.get(day) })}` : ""}${
            quakes.has(day) ? `, ${t("strip.day_quake", { magnitude: number(quakes.get(day), 1) })}` : ""
          }`;
          return (
            <div key={day} className={`day${day < first ? " lead" : ""}${pass ? " pass" : ""}`} title={title}>
              <div className="rain" style={{ height: `${(value / peak) * 100}%` }} />
              {fires.has(day) ? <span className="fire" /> : null}
            </div>
          );
        })}
      </div>

      <div className="axis" aria-hidden="true">
        {days.map((day, index) => {
          const pass = day === first || day === last;
          const show = pass || index === 0 || (index % 4 === 0 && Math.abs(days.indexOf(first) - index) > 1 && days.length - index > 2);
          return (
            <span
              key={day}
              className={`${pass ? "pass" : ""}${index === days.length - 1 ? " end" : ""}${index === 0 ? " start" : ""}`}
            >
              {show ? (pass ? `${t(day === first ? "downloads.before" : "downloads.after")} ${shortDate(day)}` : shortDate(day)) : ""}
            </span>
          );
        })}
      </div>
    </section>
  );
}
