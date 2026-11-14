import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/shared/EmptyState";
import type { ChangeEvent } from "@/types/change";

export function ChangeDistribution({ changes }: { changes: ChangeEvent[] }) {
  if (changes.length === 0) {
    return <EmptyState title="Sin cambios" description="Ejecuta un análisis para ver la distribución de áreas." />;
  }

  const data = [...changes]
    .sort((a, b) => (b.area_km2 ?? 0) - (a.area_km2 ?? 0))
    .slice(0, 8)
    .map((change) => ({
      name: change.id.slice(0, 8),
      area: Number((change.area_km2 ?? 0).toFixed(4)),
    }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: -12 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2b45" />
        <XAxis dataKey="name" stroke="#8ba0be" fontSize={11} />
        <YAxis stroke="#8ba0be" fontSize={11} />
        <Tooltip
          contentStyle={{ background: "#111b2e", border: "1px solid #1e2b45", fontSize: 12 }}
          labelStyle={{ color: "#e2e8f0" }}
        />
        <Bar dataKey="area" name="Área (km²)" fill="#f97316" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
