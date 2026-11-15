import { useQuery } from "@tanstack/react-query";
import { CloudRain, Flame, Activity, X } from "lucide-react";

import { area, db, geometryBounds, number, shortDate, significance, signedDb, typeStyle, type Bounds } from "@/observatory/lib";
import { changesService } from "@/services/changes.service";
import { evidenceService } from "@/services/evidence.service";
import type { EvidenceRecord } from "@/types/evidence";

const SCALE_MIN = -30;
const SCALE_MAX = 0;

function onScale(value: number): number {
  return ((Math.min(SCALE_MAX, Math.max(SCALE_MIN, value)) - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)) * 100;
}

/** Labels near either end of the scale hang inwards so they never clip. */
function edge(value: number): string {
  const at = onScale(value);
  return at > 72 ? " edge-right" : at < 28 ? " edge-left" : "";
}

function EvidenceRow({ record }: { record: EvidenceRecord }) {
  const event = record.event;
  if (!event) return null;
  const meta = (event.metadata ?? {}) as Record<string, unknown>;
  const where =
    record.spatial_relation === "INTERSECTS" ? "dentro del área" : `a ${number(record.distance_km, 1)} km`;

  let glyph = <Activity size={16} />;
  let color = "#b0305c";
  let title = `Sismo M${number(event.magnitude, 1)}`;
  let detail = `${shortDate(event.event_date, true)}, ${where}.`;

  if (event.event_type === "FIRE") {
    glyph = <Flame size={16} />;
    color = "#d2571b";
    title = "Foco de fuego activo";
    detail = `${shortDate(event.event_date, true)}, ${where}${
      event.magnitude != null ? `, ${number(event.magnitude, 1)} MW` : ""
    }.`;
  } else if (event.event_type === "PRECIPITATION") {
    glyph = <CloudRain size={16} />;
    color = "#1f6fb2";
    const anomaly = typeof meta.anomaly_pct === "number" ? meta.anomaly_pct : null;
    title = `${number(event.magnitude, 0)} mm de lluvia`;
    detail = `Del ${shortDate(String(meta.window_start ?? ""))} al ${shortDate(String(meta.window_end ?? ""))}${
      anomaly != null ? `, ${anomaly >= 0 ? "+" : "−"}${number(Math.abs(anomaly), 0)} % frente a lo normal` : ""
    }.`;
  }

  return (
    <div className="evidence">
      <span className="glyph" style={{ color }} aria-hidden="true">
        {glyph}
      </span>
      <div>
        <p style={{ fontWeight: 500 }}>{title}</p>
        <p className="quiet">{detail}</p>
      </div>
    </div>
  );
}

interface ChangePanelProps {
  changeId: string;
  onClose: () => void;
  onLocate: (bounds: Bounds) => void;
}

export function ChangePanel({ changeId, onClose, onLocate }: ChangePanelProps) {
  const change = useQuery({ queryKey: ["change", changeId], queryFn: () => changesService.get(changeId) });
  const metrics = useQuery({ queryKey: ["change", changeId, "metrics"], queryFn: () => changesService.metrics(changeId) });
  const evidence = useQuery({ queryKey: ["change", changeId, "evidence"], queryFn: () => evidenceService.forChange(changeId) });

  if (change.isLoading) {
    return (
      <aside className="detail">
        <div className="block quiet">Cargando el cambio…</div>
      </aside>
    );
  }
  if (change.isError || !change.data) {
    return (
      <aside className="detail">
        <div className="block">
          <p className="notice problem">No se pudo cargar este cambio. Vuelve a seleccionarlo en el mapa.</p>
        </div>
      </aside>
    );
  }

  const item = change.data;
  const type = typeStyle(item.change_type);
  const value = (name: string) => metrics.data?.find((metric) => metric.metric_name === name)?.value ?? null;
  const beforeDb = value("mean_backscatter_before_db");
  const afterDb = value("mean_backscatter_after_db");
  const threshold = value("detection_threshold_db");
  const darker = item.direction === "DECREASE";
  const records = evidence.data ?? [];

  return (
    <aside className="detail" aria-label="Detalle del cambio seleccionado">
      <div className="block">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <span className="chip">
            <i style={{ background: type.color }} />
            {area(item.area_km2)}
          </span>
          <button className="btn tonal small icon" onClick={onClose} aria-label="Cerrar el detalle">
            <X size={16} />
          </button>
        </div>
        <h2 className="title" style={{ margin: "16px 0 10px" }}>
          {type.label}
        </h2>
        <p className="quiet">{type.reading}</p>
        <button className="btn tonal small" style={{ marginTop: 16 }} onClick={() => onLocate(geometryBounds(item.geometry))}>
          Centrar en el mapa
        </button>
      </div>

      <div className="block">
        <p className="figure" style={{ color: darker ? "var(--color-darker)" : "var(--color-brighter)" }}>
          {signedDb(item.mean_change_db)}
        </p>
        <p className="quiet" style={{ marginTop: 10 }}>
          La señal de radar {darker ? "bajó" : "subió"} en promedio
          {threshold ? `, ${number(Math.abs(item.mean_change_db ?? 0) / threshold, 1)} veces el umbral de detección` : ""}.
        </p>

        {beforeDb != null && afterDb != null ? (
          <div className="dbscale" role="img" aria-label={`Antes ${db(beforeDb)}, después ${db(afterDb)}`}>
            <div className="track" />
            <div className={`pin before${edge(beforeDb)}`} style={{ left: `${onScale(beforeDb)}%` }}>
              <b>Antes {db(beforeDb)}</b>
            </div>
            <div className={`pin after${edge(afterDb)}`} style={{ left: `${onScale(afterDb)}%` }}>
              <b>Después {db(afterDb)}</b>
            </div>
          </div>
        ) : null}
        <p className="label">Oscuro a la izquierda, como el agua en calma. Brillante a la derecha, como un bosque o una ciudad.</p>
      </div>

      <div className="block">
        <dl className="facts">
          <div>
            <dt>Significancia</dt>
            <dd>{significance(item.change_score, item.area_km2)}</dd>
          </div>
          <div>
            <dt>Intensidad relativa</dt>
            <dd className="num">{number(item.change_score, 2)}</dd>
          </div>
          <div>
            <dt>Umbral de detección</dt>
            <dd className="num">{db(threshold)}</dd>
          </div>
          <div>
            <dt>Cambio más fuerte</dt>
            <dd className="num">{signedDb(value("peak_change_db"))}</dd>
          </div>
        </dl>
      </div>

      <div className="block">
        <h3>Qué pasó cerca en esos días</h3>
        {evidence.isLoading ? <p className="quiet">Buscando eventos…</p> : null}
        {!evidence.isLoading && records.length === 0 ? (
          <p className="quiet">Ningún sismo, foco de fuego ni lluvia registrados junto a este cambio.</p>
        ) : null}
        {records.slice(0, 8).map((record) => (
          <EvidenceRow key={record.id} record={record} />
        ))}
        <p className="label" style={{ marginTop: 14 }}>
          Que algo haya ocurrido cerca y en esos días es contexto, no una causa demostrada.
        </p>
      </div>
    </aside>
  );
}
