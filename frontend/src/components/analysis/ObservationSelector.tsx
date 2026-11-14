import { Select } from "@/components/ui/select";
import type { Observation } from "@/types/observation";
import { formatDateTime } from "@/utils/formatters";

export function ObservationSelector({
  observations,
  beforeId,
  afterId,
  onChange,
}: {
  observations: Observation[];
  beforeId: string | null;
  afterId: string | null;
  onChange: (kind: "before" | "after", id: string | null) => void;
}) {
  const options = observations.map((observation) => (
    <option key={observation.id} value={observation.id}>
      {formatDateTime(observation.acquisition_date)} · {observation.storage_status}
    </option>
  ));

  return (
    <div className="grid grid-cols-1 gap-2">
      <label className="flex flex-col gap-1 text-xs text-muted">
        Observación inicial (before)
        <Select
          value={beforeId ?? ""}
          onChange={(event) => onChange("before", event.target.value || null)}
          disabled={observations.length === 0}
        >
          <option value="">Selecciona una observación</option>
          {options}
        </Select>
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Observación final (after)
        <Select
          value={afterId ?? ""}
          onChange={(event) => onChange("after", event.target.value || null)}
          disabled={observations.length === 0}
        >
          <option value="">Selecciona una observación</option>
          {options}
        </Select>
      </label>
      {beforeId && beforeId === afterId ? (
        <p className="text-xs text-amber-300">
          El par debe usar dos adquisiciones distintas (el backend lo rechaza con 422).
        </p>
      ) : null}
    </div>
  );
}
