# API

Base: `http://localhost:8000/api/v1` · OpenAPI: `/docs`.

| Método | Ruta | Estado |
|---|---|---|
| GET | `/health` | implementado |
| GET | `/locations` | implementado |
| GET | `/locations/search?q=` | implementado |
| GET | `/locations/{id}` | implementado |
| GET | `/nisar/scenes` (`product_type`, `maturity`, `start`, `end`, `bbox`) | implementado |
| GET | `/nisar/scenes/{id}` | implementado |
| GET | `/observations` (`scene_id`, `location_id`, `storage_status`) | implementado |
| GET | `/observations/{id}` | implementado |
| POST | `/analysis` | implementado (encola) |
| GET | `/jobs` | implementado |
| GET | `/jobs/{id}` | implementado |
| POST | `/jobs/{id}/cancel` | implementado |
| GET | `/changes` (`job_id`, `bbox`) | implementado |
| GET | `/changes/{id}` | implementado |
| GET | `/changes/{id}/metrics` | implementado |
| GET | `/changes/{id}/evidence` | implementado |
| GET | `/changes/{id}/tiles` · `/jobs/{id}/tiles` | implementado (URLs, bounds, leyenda) |
| GET | `/changes/{id}/tiles/{z}/{x}/{y}?layer=` · `/jobs/{id}/tiles/{z}/{x}/{y}?layer=` | implementado (PNG) |
| GET | `/auxiliary/events` (`source`, `event_type`, `bbox`) | implementado |
| GET | `/insights` | implementado |

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
`minimum_valid_pixel_percentage` se mide sobre el raster del AOI: si el frame cubre
poco del AOI hay que bajarlo.

Respuesta `202`:

```json
{ "job_id": "uuid", "status": "PENDING", "progress": 0, "message": "Analysis queued successfully" }
```

Errores: `404` si falta cualquier entidad, `422` si el par es incompatible
(mensaje con todos los motivos separados por `;`), `400` por `bbox` o fechas
inválidas, `409` al cancelar un trabajo ya terminado.

`GET /jobs/{id}` incluye `parameters` (lo que se pidió) y `result` (umbral, conteo por
`change_type` y estado de cada fuente auxiliar en `evidence_sources`).

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
