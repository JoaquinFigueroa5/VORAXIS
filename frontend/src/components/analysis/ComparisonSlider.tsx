import { useState } from "react";

import { EmptyState } from "@/components/shared/EmptyState";
import { cn } from "@/utils/formatters";

/**
 * Before / after swipe. It needs XYZ tiles, which the API does not serve yet, so
 * the component states that explicitly instead of showing an empty black box.
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
        description="Los tiles raster responden 501 en esta fase. El COG de diferencia sí se genera y queda registrado en raster_assets."
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
