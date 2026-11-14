import { Badge } from "@/components/ui/badge";
import type { JobStatus } from "@/types/job";

const TONES: Record<JobStatus, "neutral" | "info" | "success" | "danger" | "warning"> = {
  PENDING: "neutral",
  RUNNING: "info",
  COMPLETED: "success",
  FAILED: "danger",
  CANCELLED: "warning",
};

export function StatusBadge({ status }: { status: JobStatus }) {
  return <Badge tone={TONES[status] ?? "neutral"}>{status}</Badge>;
}
