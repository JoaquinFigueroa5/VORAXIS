import { useState } from "react";

import { EmptyState } from "@/components/shared/EmptyState";
import { cn } from "@/utils/formatters";

/**
 * Before / after swipe. The API now serves the rasters as XYZ tiles
 * (`changesService.tiles(id)` -> layers.before / layers.after); this component
 * still expects two image URLs, so it shows a notice until it is wired to them.
 */
export function ComparisonSlider({
  beforeImage,
  afterImage,
  className,
}: {
  beforeImage?: string;
  afterImage?: string;
  className?: string;
}) {
  const [position, setPosition] = useState(50);

  if (!beforeImage || !afterImage) {
    return (
      <EmptyState
        title="Comparador before / after pendiente"
        description="El backend ya sirve los tiles antes / después / diferencia (GET /changes/{id}/tiles). Falta conectar este comparador a esas capas."
      />
    );
  }

  return (
    <div className={cn("relative overflow-hidden rounded-lg border border-surface-border", className)}>
      <img src={afterImage} alt="Después" className="h-full w-full object-cover" />
      <div
        className="absolute inset-0 overflow-hidden"
        style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}
      >
        <img src={beforeImage} alt="Antes" className="h-full w-full object-cover" />
      </div>
      <div
        className="pointer-events-none absolute inset-y-0 w-0.5 bg-accent"
        style={{ left: `${position}%` }}
      />
      <input
        type="range"
        min={0}
        max={100}
        value={position}
        onChange={(event) => setPosition(Number(event.target.value))}
        aria-label="Comparar antes y después"
        className="absolute bottom-2 left-1/2 w-2/3 -translate-x-1/2 accent-sky-400"
      />
    </div>
  );
}
