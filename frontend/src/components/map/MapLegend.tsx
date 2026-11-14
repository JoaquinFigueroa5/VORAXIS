const ITEMS = [
  { label: "AOI", color: "#38bdf8", shape: "outline" as const },
  { label: "Huellas NISAR", color: "#94a3b8", shape: "outline" as const },
  { label: "Cambios detectados", color: "#f97316", shape: "fill" as const },
  { label: "Sismos (USGS)", color: "#f59e0b", shape: "dot" as const },
  { label: "Incendios (FIRMS)", color: "#ef4444", shape: "dot" as const },
  { label: "Precipitación (GPM)", color: "#22d3ee", shape: "dot" as const },
];

export function MapLegend() {
  return (
    <div className="pointer-events-none absolute bottom-4 right-4 z-10 rounded-md border border-surface-border bg-surface-raised/90 p-3 text-xs text-slate-200">
      <p className="mb-2 font-semibold tracking-wide text-slate-100">Leyenda</p>
      <ul className="flex flex-col gap-1.5">
        {ITEMS.map((item) => (
          <li key={item.label} className="flex items-center gap-2">
            <span
              aria-hidden
              className={item.shape === "dot" ? "h-2.5 w-2.5 rounded-full" : "h-2.5 w-4 rounded-sm"}
              style={{
                backgroundColor: item.shape === "outline" ? "transparent" : item.color,
                border: item.shape === "outline" ? `1.5px solid ${item.color}` : undefined,
              }}
            />
            {item.label}
          </li>
        ))}
      </ul>
      <p className="mt-2 max-w-40 leading-relaxed text-muted">
        Los cambios se muestran como UNCLASSIFIED hasta contar con interpretación validada.
      </p>
    </div>
  );
}
