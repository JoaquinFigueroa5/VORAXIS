import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { useChangeMetrics } from "@/hooks/useChanges";
import { formatNumber } from "@/utils/formatters";

export function ChangeMetrics({ changeId }: { changeId: string }) {
  const metrics = useChangeMetrics(changeId);

  if (metrics.isLoading) return <LoadingState label="Calculando métricas…" />;
  if (metrics.isError) return <ErrorState error={metrics.error} />;
  if (!metrics.data || metrics.data.length === 0) {
    return <EmptyState title="Sin métricas" description="El trabajo no generó métricas para este cambio." />;
  }

  return (
    <table className="w-full text-left text-xs">
      <thead className="text-muted">
        <tr>
          <th className="pb-1 font-medium">Métrica</th>
          <th className="pb-1 text-right font-medium">Valor</th>
          <th className="pb-1 text-right font-medium">Unidad</th>
        </tr>
      </thead>
      <tbody>
        {metrics.data.map((metric) => (
          <tr key={metric.id} className="border-t border-surface-border/60">
            <td className="py-1.5 text-slate-200">{metric.metric_name}</td>
            <td className="py-1.5 text-right text-slate-200">{formatNumber(metric.value, 4)}</td>
            <td className="py-1.5 text-right text-muted">{metric.unit ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
