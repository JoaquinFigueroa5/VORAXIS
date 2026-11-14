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
| GET | `/changes/{id}/tiles/{z}/{x}/{y}` | **501** |
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
    "polarization": "VV",
    "minimum_valid_pixel_percentage": 80,
    "change_threshold_sigma": 2.0
  }
}
```

Respuesta `202`:

```json
{ "job_id": "uuid", "status": "PENDING", "progress": 0, "message": "Analysis queued successfully" }
```

Errores: `404` si falta cualquier entidad, `422` si el par es incompatible
(mensaje con todos los motivos separados por `;`), `400` por `bbox` o fechas
inválidas, `409` al cancelar un trabajo ya terminado.

## Convenciones

- Geometría siempre como objeto GeoJSON, nunca WKB ni WKT.
- Las listas paginan con `limit` (1–200) y `offset`.
- `change_score` y `evidence_score` son indicadores relativos, no probabilidades.
- `POST /analysis` responde `202` y no bloquea: el progreso se consulta por
  polling en `/jobs/{id}`.
