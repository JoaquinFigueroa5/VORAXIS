import { Navigation } from "@/components/layout/Navigation";

export function Sidebar() {
  return (
    <aside className="flex h-full w-60 shrink-0 flex-col gap-6 border-r border-surface-border bg-surface-raised/40 p-4">
      <div className="flex items-center gap-2">
        <img src="/logo.svg" alt="" className="h-8 w-8" />
        <div>
          <p className="text-sm font-semibold leading-tight text-slate-100">SpaceApps</p>
          <p className="text-xs text-muted">NISAR change explorer</p>
        </div>
      </div>

      <Navigation />

      <div className="mt-auto text-xs leading-relaxed text-muted">
        <p>Datos: ASF DAAC · USGS</p>
        <p>PostGIS · MinIO · Redis</p>
      </div>
    </aside>
  );
}
