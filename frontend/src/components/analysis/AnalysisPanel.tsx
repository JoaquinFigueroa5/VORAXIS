import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { ObservationSelector } from "@/components/analysis/ObservationSelector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useAnalysis } from "@/hooks/useAnalysis";
import { useObservations } from "@/hooks/useObservations";
import { useAnalysisStore } from "@/stores/analysis.store";
import { analysisRequestSchema } from "@/types/analysis";

export function AnalysisPanel({ locationId }: { locationId: string | null }) {
  const observations = useObservations({ location_id: locationId ?? undefined });
  const beforeId = useAnalysisStore((state) => state.beforeObservationId);
  const afterId = useAnalysisStore((state) => state.afterObservationId);
  const setBefore = useAnalysisStore((state) => state.setBefore);
  const setAfter = useAnalysisStore((state) => state.setAfter);

  const [polarization, setPolarization] = useState("HH");
  const [minValid, setMinValid] = useState(80);
  const [sigma, setSigma] = useState(2);
  const [validationError, setValidationError] = useState<string | null>(null);

  const mutation = useAnalysis();
  const navigate = useNavigate();

  function submit(event: FormEvent) {
    event.preventDefault();
    setValidationError(null);

    const parsed = analysisRequestSchema.safeParse({
      location_id: locationId ?? "",
      before_observation_id: beforeId ?? "",
      after_observation_id: afterId ?? "",
      analysis_type: "GCOV_CHANGE",
      parameters: {
        polarization,
        minimum_valid_pixel_percentage: minValid,
        change_threshold_sigma: sigma,
      },
    });

    if (!parsed.success) {
      setValidationError(parsed.error.issues[0]?.message ?? "Datos incompletos");
      return;
    }

    mutation.mutate(parsed.data, {
      onSuccess: (accepted) => navigate(`/analysis/${accepted.job_id}`),
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Nuevo análisis</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {!locationId ? (
          <p className="text-xs text-amber-300">Selecciona una región en el mapa primero.</p>
        ) : null}

        {observations.isLoading ? <LoadingState label="Buscando observaciones…" /> : null}
        {observations.isError ? <ErrorState error={observations.error} /> : null}

        <ObservationSelector
          observations={observations.data ?? []}
          beforeId={beforeId}
          afterId={afterId}
          onChange={(kind, id) => (kind === "before" ? setBefore(id) : setAfter(id))}
        />

        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1 text-xs text-muted">
            Polarización
            <Select value={polarization} onChange={(event) => setPolarization(event.target.value)}>
              {["HH", "HV", "VV", "VH"].map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted">
            Píxeles válidos mínimos (%)
            <Input
              type="number"
              min={0}
              max={100}
              value={minValid}
              onChange={(event) => setMinValid(Number(event.target.value))}
            />
          </label>
          <label className="col-span-2 flex flex-col gap-1 text-xs text-muted">
            Umbral de cambio (σ): {sigma}
            <input
              type="range"
              min={1}
              max={5}
              step={0.5}
              value={sigma}
              onChange={(event) => setSigma(Number(event.target.value))}
              className="accent-sky-400"
            />
          </label>
        </div>

        {validationError ? <p className="text-xs text-red-300">{validationError}</p> : null}
        {mutation.isError ? <ErrorState error={mutation.error} /> : null}

        <Button type="submit" onClick={submit} disabled={mutation.isPending}>
          {mutation.isPending ? "Encolando…" : "Solicitar análisis"}
        </Button>
        <p className="text-xs leading-relaxed text-muted">
          El backend valida madurez, versión de procesamiento, polarización y solape de huellas
          antes de encolar. El trabajo corre en el worker y se consulta por polling.
        </p>
      </CardContent>
    </Card>
  );
}
