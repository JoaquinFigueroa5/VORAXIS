import { EvidenceCard } from "@/components/evidence/EvidenceCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEvidence } from "@/hooks/useEvidence";

export function EvidencePanel({ changeId }: { changeId: string }) {
  const evidence = useEvidence(changeId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Evidencia contextual</CardTitle>
      </CardHeader>
      <CardContent>
        {evidence.isLoading ? <LoadingState label="Buscando eventos cercanos…" /> : null}
        {evidence.isError ? <ErrorState error={evidence.error} /> : null}
        {evidence.data && evidence.data.length === 0 ? (
          <EmptyState
            title="Sin eventos relacionados"
            description="No hay eventos auxiliares dentro de 50 km y ±72 h de la adquisición. La ausencia de evidencia no implica ausencia de causa."
          />
        ) : null}
        {evidence.data && evidence.data.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {evidence.data.map((record) => (
              <EvidenceCard key={record.id} record={record} />
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}
