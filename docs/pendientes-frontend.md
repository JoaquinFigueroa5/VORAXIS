# Pendientes del frontend

Estado al 15 de noviembre de 2026, rama `feat/ingesta-gcov-y-tiles` (commit `c25c149`, aún sin subir).

## Cómo levantarlo

```bash
docker compose up -d                                   # PostGIS, Redis, worker, S3, API :8000 y front :5173
docker compose exec frontend npm run typecheck         # tipos
docker compose exec backend python scripts/check_api.py   # la API contra las fuentes reales
```

- Front: <http://localhost:5173> · API: <http://localhost:8000/api/v1> · OpenAPI: <http://localhost:8000/docs>
- Antes de tocar nada, leer `docs/api.md` (todas las rutas, con ejemplos), `docs/processing-pipeline.md` y `docs/data-sources.md`.
- Hay datos de prueba ya procesados: Delta del Krishna, Machilipatnam, Trapecio Amazónico y Petén.

## Dónde está el código

Todo lo nuevo vive en `frontend/src/observatory/`:

| Archivo | Qué es |
|---|---|
| `Shell.tsx` | Barra superior y pie del inicio |
| `HomePage.tsx` | Inicio: comparador real, frase animada, análisis guardados |
| `AnalysisPage.tsx` | Vista de un análisis (`/analisis/:id`) |
| `CompareMap.tsx` | Comparador antes/después con dos mapas sincronizados |
| `ChangePanel.tsx` | Detalle de un cambio: métricas y evidencia |
| `IntervalStrip.tsx` | Tira de lluvia, focos y sismos entre las dos fechas |
| `NewAnalysisPage.tsx` | Asistente de nuevo análisis (`/nuevo`) |
| `ExplorePage.tsx` | Explorar un punto (`/explorar`) |
| `DownloadsMenu.tsx`, `downloads.ts` | Menú "Descargas" de la barra y lógica de tareas de ingesta |
| `basemap.tsx` | Selector de mapa base (gris, satélite, NASA) |
| `lib.ts` | Tipos de cambio, formatos de fecha, área y dB |
| `maplibre.ts` | Importar MapLibre **siempre desde aquí** (resuelve el worker de MapLibre 6) |

Estilos en `frontend/src/assets/styles/globals.css`. Los servicios de la API están en `frontend/src/services/` y los tipos en `frontend/src/types/`.

### Reglas del diseño (no romperlas)

- Paleta blanco, gris y tinta `#232323`. El único acento es menta `#a1ffcb` y significa **"seleccionado"**, nada más.
- Rojo `#c8322a` = la superficie se oscureció; azul `#3f6fb0` = se aclaró. No usar rojo para errores en el mapa ni azul como decoración.
- Fuentes Geist y Geist Mono (cifras con la clase `num`). Radios suaves (`--r-sm`, `--r-md`).
- Las clasificaciones son hipótesis (`POSSIBLE_*`). La interfaz no debe presentarlas como hechos.
- Textos de la interfaz en español.

## Pendientes, en orden de prioridad

### 1. Vista de análisis

- [ ] **Gráficos con `GET /jobs/{id}/insights`**: histograma de score, histograma de área, cambios que se oscurecieron frente a los que se aclararon (`by_direction`) y resumen de evidencia. Recharts ya está instalado y `insightsService.forJob(id)` ya existe. Los campos están descritos en `docs/api.md`, sección "Insights de un análisis".
- [ ] **Evidencia en el mapa**: dibujar los focos FIRMS y los sismos USGS como puntos sobre el comparador. Hoy solo aparecen en la tira inferior y en el panel de cada cambio. Datos: `/changes/{id}/evidence` o `/auxiliary/events?bbox=`.

> **No es parte de esta tarea:** los filtros de cambios (área mínima, intensidad y dirección) los hace otra persona. El detalle está en [`docs/filtros-cambios.md`](filtros-cambios.md). Esa persona también toca `AnalysisPage.tsx` y `CompareMap.tsx`: coordinarse antes de cambiar la estructura de esos archivos.

### 2. Asistente de nuevo análisis

- [ ] **Opciones avanzadas**: polarización HH/HV, umbral (`change_threshold_sigma`) y multilook. Hoy están fijos en `DEFAULT_ANALYSIS` y `DEFAULT_MULTILOOK` (`downloads.ts`). Las dos fechas de un par deben usar el mismo multilook.
- [ ] **Dibujar el polígono de la zona**. Hoy se guarda el encuadre del mapa como rectángulo. `POST /locations` ya acepta un `Polygon` GeoJSON (máximo 3° por lado).
- [ ] **Mostrar la huella del par elegido** antes de descargar, para ver cuánto de la zona cubre el radar. Cada gránulo de `/context/nisar` trae su huella.

### 3. Integración con el equipo

- [ ] **Las 5 preguntas**: otra persona hará el endpoint. Hay que mostrarlo en la vista de análisis cuando exista.
- [ ] **Componentes viejos sin usar** (`src/components`, `src/hooks`, `src/stores`, `src/features`): decidir con el equipo si se borran.

### 4. Calidad

- [ ] **Configurar ESLint**: hoy no hay configuración y `npx eslint` falla.
- [ ] **Pruebas**: el front no tiene ninguna. Lo mínimo útil: `groupBatches` (en `downloads.ts`, arma los pares de descargas) y los formateadores de `lib.ts`.
- [ ] **Bundle**: el build avisa que un chunk pasa de 500 kB. Cargar cada página con `lazy()` en `src/app/router.tsx` lo resolvería.
- [ ] **Pendiente de probar a mano**:
  - Botón **Comparar** del menú Descargas, de punta a punta (encola un análisis real).
  - Mapa base NASA después del arreglo de etiquetas.
  - Explorar y el asistente a 390 px de ancho.
- [ ] **Accesibilidad**: pasada con teclado y lector de pantalla, sobre todo en el comparador y en el panel de Descargas.

### 5. Detalles menores

- [ ] En los mapas de color, las etiquetas y fronteras blancas quedan encima del radar y pesan. Valorar ponerlas debajo de la capa `radar` (`CompareMap.tsx`).
- [ ] El mapa NASA (Blue Marble) solo llega al zoom 8: de cerca se ve borroso. Es una limitación de la fuente, no un error.

## Cosas que conviene saber

- **El worker hace una tarea a la vez**: descargas y análisis comparten cola. Un análisis lanzado durante una descarga espera a que termine.
- **Descargas**: el backend no guarda qué tareas forman un par. `groupBatches` las agrupa por zona y por haber entrado a la cola con menos de 5 s de diferencia.
- **Polling**: las consultas usan TanStack Query. `["ingest"]` se refresca cada 2,5 s si hay algo activo y `["jobs"]` cada 4 a 10 s. Reusar esas claves en vez de crear otras.
- **Capturas**: el panel del navegador integrado suele estar oculto y no dibuja. Para capturas, desde `frontend/`:
  `node ../.claude/skills/design-taste-frontend/scripts/shoot.mjs --url <url> --w 1440 --h 900 --wait 8000 --out <png> --profile .taste-skill/chrome-check --no-tiles`
- **Credenciales**: están en `VORAXIS/.env`. Nunca copiarlas a `.env.example` ni al código.
