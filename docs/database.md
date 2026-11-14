# Base de datos

PostgreSQL 16 + PostGIS 3.4. Las tablas las crea **solo** Alembic
(`backend/migrations`); `database/init` únicamente habilita PostGIS y crea los
esquemas.

| Esquema | Tablas |
|---|---|
| `geography` | `locations` |
| `catalog` | `nisar_scenes`, `observations` |
| `processing` | `processing_jobs`, `raster_assets` |
| `analysis` | `change_events`, `change_metrics` |
| `evidence` | `auxiliary_events`, `evidence_records` |

## Tipos y restricciones

- Identificadores `uuid` con `gen_random_uuid()` en la aplicación (`uuid4`).
- Geometrías `MULTIPOLYGON(4326)` salvo `auxiliary_events.geometry`, que es
  `GEOMETRY(4326)` porque puede ser punto, línea o polígono.
- `CHECK` en `processing_jobs.status` y `progress` (0–100), en
  `observations.storage_status` y en `change_events.valid_pixel_percentage`.
- `change_type` acepta `UNCLASSIFIED`; no hay catálogo cerrado de fenómenos.
- `nisar_scenes.product_id` es único: es la clave de idempotencia del catálogo.
- `evidence_records` tiene índice único `(change_event_id, auxiliary_event_id)`.

## Índices

GiST en `locations.geometry`, `nisar_scenes.footprint`,
`change_events.geometry` y `auxiliary_events.geometry`. B-tree en fechas de
adquisición, `processing_jobs.status` y el compuesto
`nisar_scenes(product_type, maturity, acquisition_start)`.

## Migraciones

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic revision --autogenerate -m "cambio"
```

`backend/migrations/env.py` filtra con `include_object` para no tocar
`public.spatial_ref_sys` ni otras tablas de PostGIS.
