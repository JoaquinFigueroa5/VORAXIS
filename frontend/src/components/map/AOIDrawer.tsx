import { Search } from "lucide-react";
import { useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import { Modal } from "@/components/shared/Modal";
import type { Location } from "@/types/location";

export function AOIDrawer({
  open,
  onClose,
  locations,
  selectedId,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  locations: Location[];
  selectedId: string | null;
  onSelect: (location: Location) => void;
}) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return locations;
    return locations.filter(
      (location) =>
        location.name.toLowerCase().includes(term) ||
        (location.country ?? "").toLowerCase().includes(term),
    );
  }, [locations, query]);

  return (
    <Modal open={open} title="Seleccionar región de interés" onClose={onClose}>
      <div className="flex flex-col gap-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por nombre o país"
            className="pl-9"
            aria-label="Buscar región"
          />
        </div>

        <ul className="flex flex-col gap-1">
          {filtered.map((location) => (
            <li key={location.id}>
              <button
                type="button"
                onClick={() => {
                  onSelect(location);
                  onClose();
                }}
                className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-surface-border/60 ${
                  selectedId === location.id ? "bg-surface-border/80 text-accent" : "text-slate-200"
                }`}
              >
                <span>{location.name}</span>
                <span className="text-xs text-muted">{location.country ?? "—"}</span>
              </button>
            </li>
          ))}
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-xs text-muted">Sin regiones que coincidan.</li>
          ) : null}
        </ul>

        <p className="border-t border-surface-border pt-3 text-xs leading-relaxed text-muted">
          Dibujar un polígono libre requiere herramientas de edición que aún no están integradas.
          Por ahora las AOI vienen del catálogo de regiones.
        </p>
      </div>
    </Modal>
  );
}
