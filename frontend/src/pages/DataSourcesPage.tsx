import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SOURCES = [
  {
    name: "NISAR · GCOV",
    role: "Detección de cambios de amplitud",
    detail:
      "Producto geocodificado y corregido por terreno. Solo GCOV tiene algoritmo implementado; GUNW, GOFF y SME2 son contratos.",
    status: "Implementado",
  },
  {
    name: "NISAR · GUNW / GOFF / SME2",
    role: "Desplazamiento, offsets y humedad del suelo",
    detail:
      "Requieren pipelines distintos (desenrollado interferométrico, campos de offset, recuperación de humedad). No se comparan con GCOV.",
    status: "Pendiente",
  },
  {
    name: "USGS FDSN",
    role: "Sismos como contexto",
    detail:
      "Consulta pública por bbox, ventana temporal y magnitud mínima. Se guarda punto, magnitud y metadatos originales.",
    status: "Implementado",
  },
  {
    name: "NASA FIRMS",
    role: "Detecciones de fuego activo",
    detail: "Contrato listo; falta el MAP_KEY y la ingesta del CSV por área.",
    status: "Contrato",
  },
  {
    name: "GPM IMERG",
    role: "Precipitación acumulada",
    detail: "Contrato listo; requiere decidir la ventana de agregación antes de persistir eventos.",
    status: "Contrato",
  },
];

export function DataSourcesPage() {
  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-slate-100">Fuentes y metodología</h1>
          <p className="text-sm leading-relaxed text-muted">
            Qué entra al sistema, qué se calcula y qué no debe interpretarse como concluyente.
          </p>
        </header>

        {SOURCES.map((source) => (
          <Card key={source.name}>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>{source.name}</CardTitle>
              <span className="text-xs text-accent">{source.status}</span>
            </CardHeader>
            <CardContent className="flex flex-col gap-1">
              <p className="text-xs font-medium text-slate-200">{source.role}</p>
              <p className="text-xs leading-relaxed text-muted">{source.detail}</p>
            </CardContent>
          </Card>
        ))}

        <Card>
          <CardHeader>
            <CardTitle>Metodología de cambios</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-xs leading-relaxed text-muted">
            <p>
              Se usa la diferencia absoluta de amplitud entre dos observaciones co-registradas, con
              umbral de k desviaciones estándar sobre la mediana. Después hay limpieza morfológica,
              poligonización y cálculo de área geodésica.
            </p>
            <p>
              <span className="text-amber-300">Limitaciones:</span> los scores son heurísticas no
              calibradas; un cambio no se etiqueta como inundación, incendio o terremoto; la
              evidencia contextual indica coincidencia espacio-temporal, no causalidad; y sin
              remuestreo no se comparan grillas distintas.
            </p>
            <p>
              Los datos de ejemplo son AOI aproximadas con fines de desarrollo, no límites
              administrativos oficiales.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
