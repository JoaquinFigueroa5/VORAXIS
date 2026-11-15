/**
 * Downloads (ingest tasks) followed from anywhere in the app.
 *
 * The backend keeps every task for 24 h but has no notion of "pair": POST /ingest
 * queues one task per product. A pair is rebuilt here from tasks of the same zone
 * queued in the same request (enqueued within a few seconds), ordered by the
 * acquisition date written in the granule name.
 */
import { useQuery } from "@tanstack/react-query";

import { analysisService } from "@/services/analysis.service";
import { ingestService } from "@/services/ingest.service";
import { jobsService } from "@/services/jobs.service";
import type { AnalysisRequest } from "@/types/analysis";
import type { IngestTask } from "@/types/ingest";
import type { ProcessingJob } from "@/types/job";

export const STAGE: Record<string, string> = {
  QUEUED: "En cola",
  DOWNLOADING: "Descargando de NASA",
  CONVERTING: "Recortando a la zona",
  UPLOADING: "Guardando",
  READY: "Lista",
};

/** What the wizard and the downloads menu ask for: HH, 3σ (fewer false positives on real data). */
export const DEFAULT_ANALYSIS: AnalysisRequest["parameters"] = {
  polarization: "HH",
  minimum_valid_pixel_percentage: 80,
  change_threshold_sigma: 3,
};
export const DEFAULT_MULTILOOK = 4;

const ACTIVE = (task: IngestTask) => task.status === "QUEUED" || task.status === "RUNNING";
const SAME_REQUEST_MS = 5_000;

export type BatchState = "active" | "failed" | "ready" | "partial";

export interface Batch {
  key: string;
  locationId: string | null;
  /** Oldest acquisition first: tasks[0] is "antes", tasks[1] "después". */
  tasks: IngestTask[];
  state: BatchState;
  enqueuedAt: number;
  /** Mean of the tasks' progress, 0-100. */
  progress: number;
  /** Observation ids when every task completed and there are exactly two. */
  pair: { before: string; after: string } | null;
}

/** "…_A_20261016T113933_20261016T114007_…" → "2026-10-16T11:39:33Z". */
export function acquisitionDate(productId: string | null): string | null {
  const match = productId?.match(/_(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})_\d{8}T/);
  if (!match) return null;
  const [, y, m, d, hh, mm, ss] = match;
  return `${y}-${m}-${d}T${hh}:${mm}:${ss}Z`;
}

function batchState(tasks: IngestTask[]): BatchState {
  if (tasks.some(ACTIVE)) return "active";
  if (tasks.some((task) => task.status === "FAILED")) return "failed";
  return tasks.length === 2 ? "ready" : "partial";
}

/** Group the flat task list into pairs, newest first; repeated requests for the same pair keep only the latest. */
export function groupBatches(tasks: IngestTask[]): Batch[] {
  const sorted = [...tasks].sort((a, b) => time(a.enqueued_at) - time(b.enqueued_at));
  const groups: IngestTask[][] = [];
  for (const task of sorted) {
    const last = groups[groups.length - 1];
    const head = last?.[0];
    if (
      head &&
      head.location_id === task.location_id &&
      time(task.enqueued_at) - time(head.enqueued_at) < SAME_REQUEST_MS
    ) {
      last.push(task);
    } else {
      groups.push([task]);
    }
  }

  const seen = new Set<string>();
  const batches: Batch[] = [];
  for (const group of groups.reverse()) {
    const ordered = [...group].sort((a, b) =>
      (acquisitionDate(a.product_id) ?? "").localeCompare(acquisitionDate(b.product_id) ?? ""),
    );
    const key = `${group[0].location_id}|${ordered.map((task) => task.product_id).join("|")}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const state = batchState(ordered);
    const observations = ordered.map((task) => task.result?.observation_id);
    batches.push({
      key,
      locationId: group[0].location_id,
      tasks: ordered,
      state,
      enqueuedAt: time(group[0].enqueued_at),
      progress: ordered.reduce((sum, task) => sum + task.progress, 0) / ordered.length,
      pair:
        state === "ready" && observations[0] && observations[1]
          ? { before: observations[0], after: observations[1] }
          : null,
    });
  }
  return batches;
}

function time(value: string | null): number {
  return value ? Date.parse(value) : 0;
}

/** Every recent download. Polls fast while something is moving, slowly otherwise. */
export function useIngestTasks() {
  return useQuery({
    queryKey: ["ingest"],
    queryFn: () => ingestService.list({ limit: 100 }),
    refetchInterval: (query) => (query.state.data?.some(ACTIVE) ? 2_500 : 30_000),
    refetchOnWindowFocus: true,
  });
}

/** Same key and request as the home page, so both share one cache entry. */
export function useJobs(fast: boolean) {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: () => jobsService.list({ limit: 100 }),
    refetchInterval: fast ? 4_000 : 10_000,
  });
}

/** The newest analysis already run on this pair, if any. */
export function jobForPair(jobs: ProcessingJob[] | undefined, pair: Batch["pair"]): ProcessingJob | null {
  if (!jobs || !pair) return null;
  return (
    jobs
      .filter((job) => job.before_observation_id === pair.before && job.after_observation_id === pair.after)
      .sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null
  );
}

export function launchAnalysis(locationId: string, pair: NonNullable<Batch["pair"]>) {
  return analysisService.create({
    location_id: locationId,
    before_observation_id: pair.before,
    after_observation_id: pair.after,
    analysis_type: "GCOV_CHANGE",
    parameters: DEFAULT_ANALYSIS,
  });
}

/** The worker reports Python exceptions; say what happened in words and keep the original for the tooltip. */
export function failureText(error: string | null): string {
  if (!error) return "No se pudo preparar una de las imágenes.";
  if (/timed out|timeout|ConnectionError|ConnectionPool|Connection reset|IncompleteRead|ChunkedEncoding/i.test(error)) {
    return "Se cortó la conexión con NASA durante la descarga. Suele ser pasajero: vuelve a intentarlo.";
  }
  if (/401|403|Unauthorized|Forbidden|credential|Earthdata/i.test(error)) {
    return "NASA Earthdata rechazó la descarga. Revisa las credenciales del servidor.";
  }
  if (/No space left|disk/i.test(error)) return "El servidor se quedó sin espacio en disco.";
  if (/not found|404/i.test(error)) return "NASA ya no ofrece este producto.";
  return error.length > 160 ? `${error.slice(0, 157)}…` : error;
}

/** Queue the same products again; whatever already finished comes back in seconds. */
export function retryBatch(batch: Batch) {
  return ingestService.create({
    location_id: batch.locationId ?? "",
    product_ids: batch.tasks.map((task) => task.product_id ?? "").filter(Boolean),
    multilook: DEFAULT_MULTILOOK,
  });
}
