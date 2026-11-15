# API

Base: `http://localhost:8000/api/v1` · OpenAPI: `/docs`.

| Método | Ruta | Estado |
|---|---|---|
| GET | `/health` | implementado |
| GET | `/locations` | implementado |
| POST | `/locations` | implementado (polígono GeoJSON o `bbox`) |
| GET | `/locations/search?q=` | implementado |
| GET | `/locations/{id}` | implementado |
| GET | `/nisar/scenes` (`product_type`, `maturity`, `start`, `end`, `bbox`) | implementado |
| GET | `/nisar/scenes/{id}` | implementado |
| GET | `/observations` (`scene_id`, `location_id`, `storage_status`) | implementado |
| GET | `/observations/{id}` | implementado |
| POST | `/ingest` | implementado (encola descarga + conversión) |
| GET | `/ingest`, `/ingest/{id}` | implementado (estado, etapa y progreso) |
| POST | `/analysis` | implementado (encola) |
| GET | `/jobs` (`status`, `location_id`, `limit`, `offset`) | implementado |
| GET | `/jobs/{id}` | implementado |
| POST | `/jobs/{id}/cancel` | implementado |
| GET | `/jobs/{id}/insights` | implementado (agregados para gráficos) |
| GET | `/jobs/{id}/changes/tiles/{z}/{x}/{y}.mvt` | implementado (tiles vectoriales) |
| GET | `/changes` (`job_id`, `bbox`, `change_type`, `direction`, `min_score`, `min_area_km2`, `sort`) | implementado |
| GET | `/changes/geojson` (mismos filtros + `zoom`) | implementado (capa de mapa) |
| GET | `/changes/{id}` | implementado |
| GET | `/changes/{id}/metrics` | implementado |
| GET | `/changes/{id}/interpretation` | implementado (clasificación, métricas, evidencia y estado de cada fuente) |
| GET | `/changes/{id}/evidence` | implementado |
| GET | `/changes/{id}/tiles` · `/jobs/{id}/tiles` | implementado (URLs, bounds, leyenda) |
| GET | `/changes/{id}/tiles/{z}/{x}/{y}?layer=` · `/jobs/{id}/tiles/{z}/{x}/{y}?layer=` | implementado (PNG) |
| GET | `/auxiliary/events` (`source`, `event_type`, `bbox`) | implementado |
| GET | `/insights` | implementado |
| GET | `/context/nisar` (`lat`, `lon`, `days` o `start`/`end`, `level`) | implementado (ASF en vivo) |
| GET | `/context/earthquakes` (`radius_km`, `min_magnitude`) | implementado (USGS en vivo) |
| GET | `/context/precipitation` | implementado (NASA POWER en vivo) |
| GET | `/context/fires` (`radius_km`) | implementado (NASA FIRMS en vivo) |
| GET | `/context/timeline` (`radius_km`) | implementado |

## Flujo completo desde el front

1. **Elegir zona**: `POST /locations` con un polígono dibujado o un `bbox`.
2. **Buscar un par**: `GET /context/nisar?lat&lon&level=GCOV` → `comparable_pairs`.
3. **Preparar los datos**: `POST /ingest` con los dos `product_id` del par y sondear
   `GET /ingest/{id}` hasta `COMPLETED`; cada resultado trae su `observation_id`.
4. **Analizar**: `POST /analysis` con las dos observaciones y sondear `GET /jobs/{id}`.
5. **Mostrar**: tiles raster, `GET /changes/geojson` o tiles vectoriales,
   `GET /jobs/{id}/insights`, y por cambio `/metrics` y `/evidence`.

## Ubicaciones

`POST /locations` (201) recibe **uno** de `geometry` (GeoJSON `Polygon`,
`MultiPolygon` o `Feature`) o `bbox` (`[oeste, sur, este, norte]`):

```json
{ "name": "Machilipatnam", "country": "India", "bbox": [80.9, 16.0, 81.4, 16.5] }
```

Errores: `400` con el motivo (área de más de 3° por lado, demasiado pequeña,
geometría inválida, coordenadas fuera de rango) y `409` si el nombre ya existe.

## Ingesta

```json
POST /ingest
{
  "location_id": "uuid",
  "product_ids": ["NISAR_L2_PR_GCOV_033_149_D_080_...", "NISAR_L2_PR_GCOV_034_149_D_080_..."],
  "multilook": 4
}
```

Responde `202` con una tarea por producto. `GET /ingest/{id}`:

```json
{
  "id": "…", "product_id": "NISAR_L2_PR_GCOV_…", "location_id": "uuid",
  "status": "RUNNING", "stage": "DOWNLOADING", "progress": 37,
  "detail": "1.80 GB de 4.89 GB", "result": null, "error": null
}
```

- `status`: `QUEUED` → `RUNNING` → `COMPLETED` | `FAILED`. `stage`: `QUEUED`,
  `DOWNLOADING`, `CONVERTING`, `UPLOADING`, `READY`. `progress` de 0 a 100.
- Al terminar, `result.observation_id` es lo que necesita `POST /analysis`.
  Si falla, `error` trae el mensaje (sin traza).
- Las tareas comparten el worker con los análisis: se ejecutan de una en una, en
  orden. Una descarga real tarda varios minutos por producto; si el archivo ya está
  en disco o la observación ya existe, termina en segundos (`result.skipped`).
- El producto no necesita estar sincronizado: se busca en ASF por nombre.
- `GET /ingest?location_id=` lista las tareas en cola, en curso y las terminadas en
  las últimas 24 h.
- `400` si el nombre no es un gránulo GCOV o faltan las credenciales de Earthdata.
- `multilook` promedia N×N píxeles (4 → 40 m). Las dos fechas de un par deben usar el
  mismo valor. `polarizations` y `force` son opcionales.

## Solicitud de análisis

```json
{
  "location_id": "uuid",
  "before_observation_id": "uuid",
  "after_observation_id": "uuid",
  "analysis_type": "GCOV_CHANGE",
  "parameters": {
    "polarization": "HH",
    "minimum_valid_pixel_percentage": 80,
    "change_threshold_sigma": 2.0,
    "smoothing_window": 5,
    "noise_floor_db": -30,
    "edge_buffer_pixels": 16,
    "minimum_area_km2": 0.01,
    "fetch_auxiliary": true
  }
}
```

Todos los parámetros son opcionales; los valores mostrados son los que se aplican
por defecto. Con datos reales `change_threshold_sigma: 3` da menos falsos positivos.
`minimum_valid_pixel_percentage` se mide sobre el área que el radar observa, no sobre
todo el AOI: un AOI mayor que el frame ya no hace fallar el análisis. Cuánto del AOI
quedó cubierto está en `job.result.aoi_coverage_percentage`.

Respuesta `202`:

```json
{ "job_id": "uuid", "status": "PENDING", "progress": 0, "message": "Analysis queued successfully", "warnings": [] }
```

`warnings` lista avisos que no impiden el análisis. Hoy uno: las dos fechas se
procesaron con versiones de software distintas (antes era un error `422`).

Errores: `404` si falta cualquier entidad, `422` si el par es incompatible
(mensaje con todos los motivos separados por `;`), `400` por `bbox` o fechas
inválidas, `409` al cancelar un trabajo ya terminado.

`GET /jobs/{id}` incluye `parameters` (lo que se pidió) y `result` (umbral, conteo por
`change_type` y estado de cada fuente auxiliar en `evidence_sources`).

## Cambios: listado, filtros y capas de mapa

`GET /changes` devuelve una página (hasta `limit=1000`) y el total que cumple los
filtros en la cabecera **`X-Total-Count`**. Cada cambio incluye `direction`
(`DECREASE` = se oscureció, `INCREASE` = se aclaró) y `mean_change_db`, así que el
mapa se puede colorear sin pedir las métricas. También trae `classification`:
`{type, label, confidence, reasons}` tal como lo guardó el clasificador.
`confidence` es `NONE`, `LOW` o `MEDIUM` — una hipótesis con la evidencia que la
sostiene, nunca una probabilidad.

| Filtro | Ejemplo |
|---|---|
| `job_id`, `bbox` | `bbox=80.9,16.0,81.4,16.5` |
| `change_type` (repetible) | `change_type=POSSIBLE_FLOODING&change_type=POSSIBLE_BURN_SCAR` |
| `direction` | `DECREASE` \| `INCREASE` |
| `min_score`, `min_area_km2` | `min_score=0.3` |
| `sort` | `area` (por defecto) \| `score` \| `newest` |

Dos formas de pintarlos:

- **`GET /changes/geojson`**: `FeatureCollection` con los mismos filtros. `zoom`
  (el zoom actual del mapa) simplifica la geometría a un píxel; `limit` hasta 10 000.
  Trae `numberMatched` y `numberReturned`; cada feature tiene `id`, `change_type`,
  `label` (en español), `direction`, `change_score`, `area_km2` y `mean_change_db`.
  1157 polígonos pesan 1,1 MB completos y 0,6 MB a zoom 9.
- **`GET /jobs/{id}/changes/tiles/{z}/{x}/{y}.mvt`**: tiles vectoriales (capa
  `changes`, mismas propiedades). Es lo más rápido con miles de polígonos:

```ts
map.addSource("changes", { type: "vector", tiles: [changesService.vectorTileTemplate(jobId)] });
map.addLayer({
  id: "changes-fill", type: "fill", source: "changes", "source-layer": "changes",
  paint: { "fill-color": ["match", ["get", "direction"], "DECREASE", "#d73027", "#4575b4"], "fill-opacity": 0.5 },
});
```

En el front: `changesService.page(filtros)` devuelve `{ items, total }`;
`changesService.geojson(filtros)`; `changesService.vectorTileTemplate(jobId)`.

## Insights de un análisis

`GET /jobs/{id}/insights` agrega en la base lo que necesitan los gráficos:

| Campo | Contenido |
|---|---|
| `totals` | cambios, área, score medio y máximo, mayor polígono, umbral, % válido y cobertura del AOI |
| `by_type` | por `change_type`: `label`, conteo, área, score medio y cambio medio en dB |
| `by_direction` | conteo y área de `DECREASE` / `INCREASE` |
| `score_histogram` | 10 intervalos de 0 a 1 |
| `area_histogram` | < 0,05 · 0,05–0,1 · 0,1–0,5 · 0,5–1 · 1–5 · > 5 km² |
| `evidence` | por tipo de evento: eventos distintos, vínculos y mejor score |
| `precipitation` | por celda: total, esperado, anomalía, día pico y serie diaria |
| `acquisitions`, `sources`, `warnings` | fechas del par, estado de cada fuente y avisos |

En el front: `insightsService.forJob(jobId)`.

## Interpretación de un cambio

`GET /changes/{id}/interpretation` reúne en una sola respuesta lo que ya está
guardado sobre ese polígono; no infiere nada nuevo:

| Campo | Contenido |
|---|---|
| `status` | `COMPLETE` solo si todas las fuentes respondieron y el cambio está clasificado; si no, `PARTIAL` |
| `period` | fechas de las dos adquisiciones e `interval_days` |
| `observation` | producto, tipo, madurez, polarización, órbita y versión de proceso de la fecha inicial |
| `change` | tipo, etiqueta en español, área, score, % válido, dirección y cambio medio en dB |
| `classification` | `confidence` y `reasons`: por qué el clasificador propuso esa etiqueta |
| `metrics` | métricas del polígono con nombre, etiqueta y unidad |
| `evidence` | eventos auxiliares vinculados, con distancia y diferencia temporal |
| `sources` | estado por fuente: `AVAILABLE`, `UNAVAILABLE` o `NOT_CONFIGURED`, y cuántos eventos encontró |
| `limitations` | frases ya redactadas sobre lo que no se puede concluir, incluida la fuente que faltó |

En el front: `interpretationService.forChange(changeId)`.

## Insights globales

`GET /insights` devuelve los totales (ubicaciones, escenas, observaciones, jobs por
estado, cambios, área, evidencias, eventos auxiliares) y cuatro distribuciones
sobre todos los análisis: `by_type`, `by_direction`, `by_month` (mes de proceso) y
`by_location`. Cada fila lleva conteo y `area_km2`; las listas quedan vacías
mientras no haya cambios, y la interfaz muestra «datos insuficientes» en vez de
una gráfica con dos puntos.

## Contexto por punto (`/context/*`)

Consultas en vivo para **cualquier** coordenada, sin escena ingerida ni ubicación
registrada. Todas reciben `lat` y `lon`, y la ventana como `days` (los últimos N
días) o `start`/`end` (`YYYY-MM-DD`, para una ventana pasada). Cada respuesta trae
`source`, `endpoint` y `retrieved_at`.

| Ruta | Devuelve |
|---|---|
| `/context/nisar` | productos NISAR sobre el punto: `granules` (nivel, track, frame, antigüedad, tamaño, vista previa, descarga, huella), `latest_by_level`, `count_by_level` y `comparable_pairs` |
| `/context/earthquakes` | sismos USGS en `radius_km` con `distance_km`; además `nearest`, `strongest` y `max_magnitude` |
| `/context/precipitation` | serie diaria (`series`), `total_mm`, `expected_mm`, `anomaly_pct`, `max_daily_mm`, `peak_date` y `elevation_m`; `available: false` si POWER aún no publica esas fechas |
| `/context/fires` | focos FIRMS en `radius_km` con `distance_km`, `frp_mw` y `confidence`; `detections_by_day`. Máximo 31 días por consulta |
| `/context/timeline` | todo lo anterior por fecha, del más reciente al más antiguo: adquisiciones GCOV, sismos, días de lluvia ≥ 20 mm y días con focos. `sources` indica qué fuente respondió |

- **`comparable_pairs`** son parejas de fechas GCOV consecutivas del mismo track,
  frame, dirección, polarización y madurez: los pares antes/después que el análisis
  puede usar. Indican `interval_days`, `download_gb` y `same_processing_version`.
- Las respuestas se cachean 10 minutos (`CONTEXT_CACHE_TTL`, en segundos).
- Errores: `502` si la fuente no responde o falta su clave (FIRMS), con el motivo en
  `detail`; `400` por ventana inválida. En `timeline` una fuente caída no es error:
  aparece con `status: "error"` en `sources`.
- En el front: `contextService.nisar | earthquakes | precipitation | fires | timeline`.

```bash
curl "http://localhost:8000/api/v1/context/timeline?lat=16.30&lon=81.10&start=2026-10-15&end=2026-11-05&radius_km=300"
```

## Verificación contra las APIs reales

```bash
docker compose exec backend python scripts/check_api.py
```

Recorre la API en ejecución (salud, datos guardados, las cinco rutas de contexto,
validación de entradas y, si hay un análisis terminado, cambios, métricas,
evidencia y tiles) contra los servicios reales, sin simulaciones. Sale con código
distinto de 0 si algo falla; lo que depende de datos ausentes se marca como omitido.

## Tiles raster (mapa y comparador)

`GET /jobs/{job_id}/tiles` (o `/changes/{change_id}/tiles`) devuelve lo necesario
para agregar las capas a MapLibre:

```json
{
  "bounds": [-90.66, 15.90, -88.96, 17.84],
  "minzoom": 0,
  "maxzoom": 12,
  "polarization": "HH",
  "layers": {
    "before": "/api/v1/jobs/<id>/tiles/{z}/{x}/{y}?layer=before",
    "after": "/api/v1/jobs/<id>/tiles/{z}/{x}/{y}?layer=after",
    "difference": "/api/v1/jobs/<id>/tiles/{z}/{x}/{y}?layer=difference",
    "mask": "/api/v1/jobs/<id>/tiles/{z}/{x}/{y}?layer=mask"
  },
  "legend": { "difference": { "units": "dB", "min": -6, "max": 6, "negative": "#d73027", "positive": "#4575b4" } }
}
```

- Las rutas de `layers` son relativas al origen del servidor (`http://localhost:8000`).
- Cada tile es un PNG RGBA de 256 px; fuera del raster llega un PNG transparente
  (200), no un error, para que el mapa no registre fallos.
- `layer` = `before` | `after` | `difference` (por defecto) | `mask`.
  `polarization=HV` cambia la banda de `before`/`after`.
- En el front: `changesService.tiles(id)` y `changesService.tileTemplate(id, layer)`;
  el resultado va directo a `<RasterLayer tilesUrl=... />`.
- `GET /changes/{id}/metrics` trae por polígono `mean_change_db`,
  `mean_backscatter_before_db` / `_after_db` y, en `metadata.direction`,
  `DECREASE` o `INCREASE`.

## Convenciones

- Geometría siempre como objeto GeoJSON, nunca WKB ni WKT.
- Las listas paginan con `limit` (1–200) y `offset`.
- `change_score` y `evidence_score` son indicadores relativos, no probabilidades.
- `POST /analysis` responde `202` y no bloquea: el progreso se consulta por
  polling en `/jobs/{id}`.
