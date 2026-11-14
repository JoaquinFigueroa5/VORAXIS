import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { InsightsSummary } from "@/types/analysis";

export function TrendChart({ jobs }: { jobs: InsightsSummary["jobs"] }) {
  const data = Object.entries(jobs).map(([status, count]) => ({ status, count }));

  if (data.length === 0) {
    return <p className="p-4 text-xs text-muted">Todavía no hay trabajos registrados.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2b45" />
        <XAxis dataKey="status" stroke="#8ba0be" fontSize={11} />
        <YAxis stroke="#8ba0be" fontSize={11} allowDecimals={false} />
        <Tooltip
          contentStyle={{ background: "#111b2e", border: "1px solid #1e2b45", fontSize: 12 }}
          labelStyle={{ color: "#e2e8f0" }}
        />
        <Bar dataKey="count" name="Trabajos" fill="#38bdf8" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
