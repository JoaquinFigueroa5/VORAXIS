import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import {
  STAGE,
  acquisitionDate,
  downloadedText,
  failureText,
  groupBatches,
  jobForPair,
  launchAnalysis,
  retryBatch,
  useIngestTasks,
  useJobs,
  type Batch,
} from "@/observatory/downloads";
import { number, shortDate } from "@/observatory/lib";
import { ApiError } from "@/services/api";
import { locationsService } from "@/services/locations.service";
import type { ProcessingJob } from "@/types/job";

const JOB_STATE: Record<string, string> = {
  PENDING: "Análisis en cola",
  RUNNING: "Analizando",
  COMPLETED: "Análisis listo",
  FAILED: "El análisis falló",
  CANCELLED: "Análisis cancelado",
};

function ArrowDown() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M8 2.5v8M4.5 7 8 10.5 11.5 7M3 13.5h10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * The header's window onto the worker: downloads in the queue, in progress and
 * from the last 24 h, wherever the user is. A finished pair can be compared from here.
 */
export function DownloadsMenu() {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement | null>(null);
  const panelId = useId();
  const route = useLocation();

  const ingest = useIngestTasks();
  const batches = useMemo(() => groupBatches(ingest.data ?? []), [ingest.data]);
  const active = batches.filter((batch) => batch.state === "active");
  const jobs = useJobs(open);
  const waiting = batches.filter((batch) => batch.pair && !jobForPair(jobs.data, batch.pair));

  // Close on navigation, outside click and Escape.
  useEffect(() => setOpen(false), [route.pathname]);
  useEffect(() => {
    if (!open) return;
    const away = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("pointerdown", away);
      document.removeEventListener("keydown", key);
    };
  }, [open]);

  if (batches.length === 0) return null;

  const progress = active.length
    ? active.reduce((sum, batch) => sum + batch.progress, 0) / active.length
    : null;
  const summary =
    progress !== null
      ? `${number(progress, 0)} %`
      : waiting.length
        ? `${waiting.length} ${waiting.length === 1 ? "lista" : "listas"}`
        : null;

  return (
    <div className="downloads" ref={root}>
      <button
        type="button"
        className={`downloads__trigger${active.length ? " busy" : ""}`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        <ArrowDown />
        <span className="downloads__word">Descargas</span>
        {summary ? <span className="downloads__count num">{summary}</span> : null}
        {progress !== null ? (
          <span className="downloads__track" aria-hidden="true">
            <i style={{ transform: `scaleX(${progress / 100})` }} />
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="downloads__panel" id={panelId} role="region" aria-label="Descargas de NISAR">
          <div className="downloads__head">
            <strong>Descargas</strong>
            <span className="label">Últimas 24 horas</span>
          </div>
          <ul className="downloads__list">
            {batches.map((batch) => (
              <BatchRow key={batch.key} batch={batch} jobs={jobs.data} onDone={() => setOpen(false)} />
            ))}
          </ul>
          <p className="downloads__foot label">
            El servidor descarga una imagen a la vez. Puedes cerrar esta ventana o cambiar de página: la descarga sigue.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function BatchRow({ batch, jobs, onDone }: { batch: Batch; jobs: ProcessingJob[] | undefined; onDone: () => void }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const locations = useQuery({ queryKey: ["locations"], queryFn: () => locationsService.list(200) });
  const zone = locations.data?.find((item) => item.id === batch.locationId)?.name ?? "Zona";
  const job = jobForPair(jobs, batch.pair);
  const [first, second] = batch.tasks.map((task) => acquisitionDate(task.product_id));
  const failedError = batch.tasks.find((task) => task.status === "FAILED")?.error ?? null;

  async function compare() {
    if (!batch.locationId || !batch.pair) return;
    setBusy(true);
    setProblem(null);
    try {
      const accepted = await launchAnalysis(batch.locationId, batch.pair);
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      onDone();
      navigate(`/analisis/${accepted.job_id}`);
    } catch (error) {
      setProblem(error instanceof ApiError || error instanceof Error ? error.message : "No se pudo iniciar el análisis.");
      setBusy(false);
    }
  }

  async function retry() {
    setBusy(true);
    setProblem(null);
    try {
      await retryBatch(batch);
      await queryClient.invalidateQueries({ queryKey: ["ingest"] });
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "No se pudo volver a encolar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="downloads__item" data-state={batch.state}>
      <div className="downloads__title">
        <strong>{zone}</strong>
        <span className="label">
          {first ? shortDate(first) : "sin fecha"}
          {second ? ` a ${shortDate(second, true)}` : ""}
        </span>
      </div>

      {batch.state === "active" || batch.state === "failed" ? (
        <div className="downloads__tasks">
          {batch.tasks.map((task, index) => (
            <div key={task.id}>
              <div className="downloads__task">
                <span>{batch.tasks.length === 2 ? (index === 0 ? "Antes" : "Después") : "Imagen"}</span>
                <span className="quiet">
                  {task.status === "FAILED" ? "Falló" : STAGE[task.stage ?? "QUEUED"]}
                  {task.status !== "COMPLETED" && downloadedText(task) ? `, ${downloadedText(task)}` : ""}
                </span>
              </div>
              <div className="bar" data-failed={task.status === "FAILED" || undefined}>
                <i style={{ transform: `scaleX(${task.progress / 100})` }} />
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {batch.state === "failed" ? (
        <>
          <p className="downloads__error" title={failedError ?? undefined}>
            {failureText(failedError)}
          </p>
          <button className="btn tonal small" disabled={busy} onClick={retry}>
            {busy ? "Encolando…" : "Reintentar"}
          </button>
        </>
      ) : null}

      {batch.state === "ready" && job ? (
        <div className="downloads__row">
          <span className="quiet">
            {JOB_STATE[job.status] ?? job.status}
            {job.status === "RUNNING" ? `, ${job.progress} %` : ""}
          </span>
          <Link className="btn tonal small" to={`/analisis/${job.id}`} onClick={onDone}>
            Ver análisis
          </Link>
        </div>
      ) : null}

      {batch.state === "ready" && !job ? (
        <div className="downloads__row">
          <span className="quiet">Las dos imágenes están listas</span>
          <button className="btn small" disabled={busy} onClick={compare}>
            {busy ? "Iniciando…" : "Comparar"}
          </button>
        </div>
      ) : null}

      {batch.state === "partial" ? <p className="quiet">Imagen preparada. Elige su par en Nuevo análisis.</p> : null}

      {problem ? <p className="downloads__error">{problem}</p> : null}
    </li>
  );
}
