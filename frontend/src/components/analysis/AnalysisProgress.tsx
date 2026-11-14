import { StatusBadge } from "@/components/shared/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProcessingJob } from "@/types/job";
import { formatDateTime } from "@/utils/formatters";

const STEPS = [
  "DOWNLOADING",
  "PREPROCESSING",
  "ALIGNMENT",
  "CHANGE_DETECTION",
  "VECTORIZATION",
  "EVIDENCE_ANALYSIS",
  "EXPORTING",
];

export function AnalysisProgress({ job }: { job: ProcessingJob }) {
  const currentIndex = job.current_step ? STEPS.indexOf(job.current_step) : -1;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Progreso del trabajo</CardTitle>
        <StatusBadge status={job.status} />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="h-2 w-full overflow-hidden rounded-full bg-surface-border">
          <div
            className="h-full bg-accent transition-all"
            style={{ width: `${job.progress}%` }}
            role="progressbar"
            aria-valuenow={job.progress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>

        <ol className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          {STEPS.map((step, index) => (
            <li
              key={step}
              className={
                index === currentIndex
                  ? "font-medium text-accent"
                  : index < currentIndex
                    ? "text-slate-300"
                    : "text-muted/60"
              }
            >
              {index < currentIndex ? "✓ " : index === currentIndex ? "▸ " : "· "}
              {step}
            </li>
          ))}
        </ol>

        <dl className="grid grid-cols-2 gap-2 text-xs text-muted">
          <div>
            <dt>Creado</dt>
            <dd className="text-slate-200">{formatDateTime(job.created_at)}</dd>
          </div>
          <div>
            <dt>Finalizado</dt>
            <dd className="text-slate-200">{formatDateTime(job.finished_at)}</dd>
          </div>
        </dl>

        {job.error_message ? (
          <p className="rounded-md border border-red-500/30 bg-red-500/10 p-2 text-xs leading-relaxed text-red-200">
            {job.error_message}
          </p>
        ) : null}

        {job.status === "PENDING" || job.status === "RUNNING" ? (
          <p className="text-xs text-muted">Actualizando cada 2 s mientras el trabajo esté activo.</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
