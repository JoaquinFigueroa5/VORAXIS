# database/

## `init/`
Scripts that PostgreSQL runs **once**, on the first start of the `postgres_data`
volume:

- `01_extensions.sql` → `CREATE EXTENSION postgis`.
- `02_schemas.sql` → `geography`, `catalog`, `processing`, `analysis`, `evidence`.

Tables are **not** created here. Alembic is the only owner of the DDL
(`backend/migrations`). Two sources of truth for tables is how projects end up
with schemas that disagree.

## `seeds/`
`locations.geojson` holds three approximate AOIs used for development.
They are deliberately rough polygons, not official administrative boundaries.
Load them with:

```bash
docker compose exec backend python scripts/seed_locations.py
```

The script is idempotent: it matches by `name` and does not duplicate rows.

## Reset

```bash
docker compose down -v   # drops postgres_data and minio_data
```
