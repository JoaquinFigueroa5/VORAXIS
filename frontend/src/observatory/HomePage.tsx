import { useQuery } from "@tanstack/react-query";
import { Satellite } from "lucide-react";
import { Fragment, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useInView } from "@/hooks/useInView";
import { useT } from "@/i18n";
import { CompareMap } from "@/observatory/CompareMap";
import { area, number, shortDate, signedDb, typeStyle } from "@/observatory/lib";
import { apiFetch } from "@/services/api";
import { insightsService } from "@/services/insights.service";
import { jobsService } from "@/services/jobs.service";
import { locationsService } from "@/services/locations.service";
import { observationsService } from "@/services/observations.service";
import { useLocale } from "@/stores/locale";
import type { TileDescription } from "@/types/change";
import type { ProcessingJob } from "@/types/job";

const LIST_LIMIT = 6;

/** The headline enters word by word, one line per "|"; NISAR keeps the mono face of a measured value. */
function heroTitle(text: string): string[][] {
  return text.split("|").map((line) => line.trim().split(/\s+/));
}

const FILTERS = [
  { id: "ALL", label: "home.filter.all" },
  { id: "DONE", label: "home.filter.done" },
  { id: "CHANGED", label: "home.filter.changed" },
  { id: "ACTIVE", label: "home.filter.active" },
] as const;

type FilterId = (typeof FILTERS)[number]["id"];

function changeCount(job: ProcessingJob): number {
  return typeof job.result?.change_events === "number" ? job.result.change_events : 0;
}

/** Every type the classifier found, most frequent first. */
function changeMix(job: ProcessingJob): [string, number][] {
  const types = (job.result?.change_types ?? {}) as Record<string, number>;
  return Object.entries(types)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1]);
}

function matches(job: ProcessingJob, filter: FilterId): boolean {
  if (filter === "DONE") return job.status === "COMPLETED";
  if (filter === "CHANGED") return job.status === "COMPLETED" && changeCount(job) > 0;
  if (filter === "ACTIVE") return job.status === "PENDING" || job.status === "RUNNING";
  return true;
}

function filterCount(jobs: ProcessingJob[], filter: FilterId): number {
  return jobs.filter((job) => matches(job, filter)).length;
}

function summarise(jobs: ProcessingJob[]) {
  return jobs.reduce(
    (summary, job) => {
      summary.total += 1;
      if (job.status === "COMPLETED") summary.completed += 1;
      if (job.status === "PENDING" || job.status === "RUNNING") summary.active += 1;
      summary.changes += changeCount(job);
      return summary;
    },
    { total: 0, completed: 0, changes: 0, active: 0 },
  );
}

/**
 * A measured figure that climbs to its value the first time its section is seen.
 * Only transform-free number changes: the layout never moves. Reduced motion gets
 * the final figure straight away.
 */
function CountUp({ to, active, duration = 900 }: { to: number; active: boolean; duration?: number }) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!active) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setValue(to);
      return;
    }

    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      setValue(Math.round(to * (1 - Math.pow(1 - progress, 3))));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [active, to, duration]);

  return <>{number(value, 0)}</>;
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
 * The three figures underneath arrive together the first time they are seen.
 */
function Statement() {
  const t = useT();
  const section = useRef<HTMLElement | null>(null);
  const facts = useInView<HTMLDListElement>();

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
      <div className="radar" aria-hidden="true" />
      <div className="wrap">
        <h2 id="statement-h" className="mo-wh__text">
          {t("home.statement.lead")} <strong>{t("home.statement.strong")}</strong>
        </h2>
        <dl className="facts-row" ref={facts.ref} data-in={facts.inView ? "true" : undefined}>
          <div>
            <dt className="num">
              <CountUp to={12} active={facts.inView} /> {t("home.unit.days")}
            </dt>
            <dd>{t("home.fact.revisit")}</dd>
          </div>
          <div>
            <dt className="num">
              <CountUp to={10} active={facts.inView} /> m
            </dt>
            <dd>{t("home.fact.pixel")}</dd>
          </div>
          <div>
            <dt className="num">
              <CountUp to={24} active={facts.inView} /> cm
            </dt>
            <dd>{t("home.fact.wavelength")}</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}

export function HomePage() {
  const navigate = useNavigate();
  const t = useT();
  const locale = useLocale((state) => state.locale);
  const title = heroTitle(t("home.hero.title"));
  const [all, setAll] = useState(false);
  const [filter, setFilter] = useState<FilterId>("ALL");
  const saved = useInView<HTMLElement>();
  const runs = useInView<HTMLDivElement>();
  const art = useRef<HTMLDivElement | null>(null);

  // A short drift plus a shallow tilt, only where there is a real pointer and no reduced-motion request.
  useEffect(() => {
    const element = art.current;
    if (!element) return;

    const fine = window.matchMedia("(hover: hover) and (pointer: fine)");
    const still = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!fine.matches || still.matches) return;

    const move = (event: PointerEvent) => {
      const box = element.getBoundingClientRect();
      const x = (event.clientX - box.left) / box.width - 0.5;
      const y = (event.clientY - box.top) / box.height - 0.5;
      element.style.setProperty("--px", `${x * -10}px`);
      element.style.setProperty("--py", `${y * -10}px`);
      element.style.setProperty("--rx", `${y * -2.6}deg`);
      element.style.setProperty("--ry", `${x * 2.6}deg`);
    };
    const reset = () => {
      element.style.setProperty("--px", "0px");
      element.style.setProperty("--py", "0px");
      element.style.setProperty("--rx", "0deg");
      element.style.setProperty("--ry", "0deg");
    };

    element.addEventListener("pointermove", move);
    element.addEventListener("pointerleave", reset);
    return () => {
      element.removeEventListener("pointermove", move);
      element.removeEventListener("pointerleave", reset);
    };
  }, []);

  const jobs = useQuery({ queryKey: ["jobs"], queryFn: () => jobsService.list({ limit: 100 }), refetchInterval: 10_000 });
  const locations = useQuery({ queryKey: ["locations"], queryFn: () => locationsService.list(200) });
  const observations = useQuery({ queryKey: ["observations"], queryFn: () => observationsService.list({ limit: 200 }) });

  const place = new Map((locations.data ?? []).map((location) => [location.id, location]));
  const date = new Map((observations.data ?? []).map((observation) => [observation.id, observation.acquisition_date]));

  const summary = useMemo(() => summarise(jobs.data ?? []), [jobs.data]);
  const counts = useMemo(() => {
    const rows = jobs.data ?? [];
    return {
      ALL: rows.length,
      DONE: filterCount(rows, "DONE"),
      CHANGED: filterCount(rows, "CHANGED"),
      ACTIVE: filterCount(rows, "ACTIVE"),
    } satisfies Record<FilterId, number>;
  }, [jobs.data]);
  const filtered = useMemo(() => (jobs.data ?? []).filter((job) => matches(job, filter)), [jobs.data, filter]);
  const visible = all ? filtered : filtered.slice(0, LIST_LIMIT);
  const remaining = filtered.length - LIST_LIMIT;

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
            <p className="hero-kicker">
              <Satellite size={14} aria-hidden="true" />
              {t("home.hero.kicker")}
            </p>
            <h1 className="hero-title">
              {title.map((line, lineIndex) => {
                const before = title.slice(0, lineIndex).reduce((total, words) => total + words.length, 0);
                return (
                  <span className="hl" key={lineIndex}>
                    {line.map((word, wordIndex) => (
                      <Fragment key={`${lineIndex}-${word}`}>
                        <span className="hw">
                          <span
                            className={word === "NISAR" ? "hw-in hw-mono" : "hw-in"}
                            style={{ "--wd": before + wordIndex } as CSSProperties}
                          >
                            {word}
                          </span>
                        </span>
                        {lineIndex < title.length - 1 || wordIndex < line.length - 1 ? " " : null}
                      </Fragment>
                    ))}
                  </span>
                );
              })}
            </h1>
            <p className="lead">
              {t("home.hero.lead")}
            </p>
            <div className="actions">
              <Link className="btn" to="/nuevo">
                {t("shell.footer.cta")}
              </Link>
              {featured ? (
                <Link className="btn tonal" to={`/analisis/${featured.id}`}>
                  {t("home.hero.latest")}
                </Link>
              ) : null}
            </div>
            {featured && top && featuredPlace ? (
              <Link className="proof proof-link" to={`/analisis/${featured.id}`}>
                <span>
                  {t("home.hero.proof", {
                    place: featuredPlace.name,
                    area: area(top.area_km2),
                    type: typeStyle(top.change_type).label.toLowerCase(),
                    from: shortDate(before),
                    to: shortDate(after, true),
                  })}
                </span>
                <svg width="18" height="12" viewBox="0 0 18 12" fill="none" aria-hidden="true">
                  <path
                    d="M1 6h15M11 1l5 5-5 5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </Link>
            ) : (
              <p className="proof">
                {t("home.hero.proof_empty")}
              </p>
            )}
          </div>

          <div className="art" ref={art}>
            <div className="window">
              <div className="bar-top">
                <strong>{featuredPlace?.name ?? t("home.window.zone")}</strong>
                <span className="label">
                  {before && after ? t("home.range", { from: shortDate(before), to: shortDate(after, true) }) : t("home.window.passes")}
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
                <p className="label">{t("home.result.areas", { count: number(top.count, 0) })}</p>
                <dl>
                  <dt>{t("home.result.mean_change")}</dt>
                  <dd className="num">{signedDb(top.mean_change_db)}</dd>
                  {rain?.total_mm != null ? (
                    <>
                      <dt>{t("home.result.rain")}</dt>
                      <dd className="num">{number(rain.total_mm, 0)} mm</dd>
                    </>
                  ) : null}
                </dl>
              </div>
            ) : null}
          </div>
        </div>

        <div className="hero-rail">
          <dl className="hero-rail-in" aria-label={t("home.rail.aria")}>
            <div>
              <dt>{t("home.stat.analyses")}</dt>
              <dd className="num">{number(summary.total, 0)}</dd>
            </div>
            <div>
              <dt>{t("home.stat.changes")}</dt>
              <dd className="num">{number(summary.changes, 0)}</dd>
            </div>
            <div>
              <dt>{t("home.rail.latest")}</dt>
              <dd>{featuredPlace?.name ?? t("home.rail.none")}</dd>
            </div>
            <div>
              <dt>{t("home.rail.revisit")}</dt>
              <dd className="num">12 {t("home.unit.days")}</dd>
            </div>
          </dl>
        </div>
      </section>

      {/* The word-highlight moment wraps the words it finds: a new language mounts it again. */}
      <Statement key={locale} />

      <section
        className="saved"
        id="analisis"
        ref={saved.ref}
        data-in={saved.inView ? "true" : undefined}
        aria-labelledby="analisis-h"
      >
        <div className="wrap">
          <div className="head">
            <div>
              <h2 id="analisis-h">{t("shell.footer.saved")}</h2>
              <p className="live" data-on={jobs.isFetching ? "true" : undefined}>
                <i aria-hidden="true" />
                {t(
                  jobs.isError
                    ? "home.live.offline"
                    : jobs.isLoading
                      ? "home.live.loading"
                      : jobs.isFetching
                        ? "home.live.updating"
                        : "home.live.idle",
                )}
              </p>
            </div>
            <Link className="btn tonal" to="/nuevo">
              {t("shell.footer.new")}
            </Link>
          </div>

          {jobs.isError ? (
            <p className="notice problem">
              {t("home.api_down")}{" "}
              <button className="linkbtn" onClick={() => jobs.refetch()}>
                {t("action.retry")}
              </button>
            </p>
          ) : null}

          {jobs.data && jobs.data.length === 0 ? (
            <div className="empty">
              <Satellite size={20} aria-hidden="true" />
              <div>
                <p style={{ fontWeight: 500 }}>{t("home.empty.title")}</p>
                <p className="quiet" style={{ marginTop: 4 }}>
                  {t("home.empty.body")}
                </p>
              </div>
              <Link className="btn" to="/nuevo">
                {t("shell.footer.cta")}
              </Link>
            </div>
          ) : null}

          {jobs.data && jobs.data.length > 0 ? (
            <>
              <dl className="stats" aria-label={t("home.stats.aria")}>
                <div>
                  <dt>{t("home.stat.analyses")}</dt>
                  <dd className="num">
                    <CountUp to={summary.total} active={saved.inView} />
                  </dd>
                </div>
                <div>
                  <dt>{t("home.stat.completed")}</dt>
                  <dd className="num">
                    <CountUp to={summary.completed} active={saved.inView} />
                  </dd>
                </div>
                <div>
                  <dt>{t("home.stat.changes")}</dt>
                  <dd className="num">
                    <CountUp to={summary.changes} active={saved.inView} duration={1200} />
                  </dd>
                </div>
                <div>
                  <dt>{t("home.stat.active")}</dt>
                  <dd className="num">
                    <CountUp to={summary.active} active={saved.inView} />
                  </dd>
                </div>
              </dl>

              <div className="saved-tools">
                <div
                  className="segmented"
                  role="group"
                  aria-label={t("home.filter.aria")}
                  style={
                    {
                      "--n": FILTERS.length,
                      "--i": FILTERS.findIndex((option) => option.id === filter),
                    } as CSSProperties
                  }
                >
                  {FILTERS.map((option) => (
                    <button
                      key={option.id}
                      aria-pressed={filter === option.id}
                      onClick={() => {
                        setFilter(option.id);
                        setAll(false);
                      }}
                    >
                      {t(option.label)}
                      <span className="tab-count">{number(counts[option.id], 0)}</span>
                    </button>
                  ))}
                </div>
              </div>

              {filtered.length === 0 ? (
                <p className="notice">
                  {t("home.filter.none")}{" "}
                  <button className="linkbtn" onClick={() => setFilter("ALL")}>
                    {t("home.filter.see_all")}
                  </button>
                </p>
              ) : (
                <div className="runs-wrap" ref={runs.ref} data-in={runs.inView ? "true" : undefined}>
                  <table className="runs">
                    <thead>
                      <tr>
                        <th>{t("home.table.zone")}</th>
                        <th>{t("home.table.dates")}</th>
                        <th>{t("home.table.areas")}</th>
                        <th>{t("home.table.top")}</th>
                        <th>{t("home.table.status")}</th>
                        <th aria-hidden="true" />
                      </tr>
                    </thead>
                    <tbody>
                      {visible.map((job, index) => {
                        const location = place.get(job.location_id);
                        const mix = changeMix(job);
                        const type = mix[0]?.[0] ?? null;
                        const mixTotal = mix.reduce((total, [, count]) => total + count, 0);
                        const open = () => navigate(`/analisis/${job.id}`);
                        return (
                          <tr
                            key={job.id}
                            className="link"
                            tabIndex={0}
                            style={{ "--row": Math.min(index, 8) } as CSSProperties}
                            onClick={open}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") open();
                            }}
                          >
                            <td>
                              <span className="place">{location?.name ?? t("home.table.unnamed")}</span>
                              {location?.country ? <span className="quiet"> {location.country}</span> : null}
                            </td>
                            <td>
                              {t("home.range", {
                                from: shortDate(date.get(job.before_observation_id)),
                                to: shortDate(date.get(job.after_observation_id), true),
                              })}
                            </td>
                            <td>
                              {job.status === "COMPLETED" ? (
                                <>
                                  <span className="num">{number(changeCount(job), 0)}</span>
                                  {mix.length > 1 ? (
                                    <span className="mix" aria-hidden="true">
                                      {mix.map(([kind, count]) => (
                                        <i
                                          key={kind}
                                          style={{
                                            width: `${(count / Math.max(mixTotal, 1)) * 100}%`,
                                            background: typeStyle(kind).color,
                                          }}
                                        />
                                      ))}
                                    </span>
                                  ) : null}
                                  <span className="sr-only">
                                    {mix
                                      .map(([kind, count]) => `${number(count, 0)} ${typeStyle(kind).label}`)
                                      .join(", ")}
                                  </span>
                                </>
                              ) : null}
                            </td>
                            <td>
                              {type ? (
                                <span className="chip">
                                  <i style={{ background: typeStyle(type).color }} />
                                  {typeStyle(type).label}
                                </span>
                              ) : null}
                            </td>
                            <td className="quiet">{t(`home.status.${job.status}`, null, job.status)}</td>
                            <td style={{ textAlign: "right" }}>
                              <span className="go" aria-hidden="true">
                                <svg width="18" height="12" viewBox="0 0 18 12" fill="none">
                                  <path
                                    d="M1 6h15M11 1l5 5-5 5"
                                    stroke="currentColor"
                                    strokeWidth="1.5"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  />
                                </svg>
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  {remaining > 0 ? (
                    <button className="btn tonal" style={{ marginTop: 24 }} onClick={() => setAll(!all)}>
                      {all ? t("home.show_less") : t("home.show_more", { count: remaining })}
                    </button>
                  ) : null}
                </div>
              )}
            </>
          ) : null}
        </div>
      </section>
    </>
  );
}
