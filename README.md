# SpaceApps NISAR

Detección de cambios con NISAR: catálogo ASF, trabajos de análisis asíncronos,
cambios vectorizados y evidencia contextual.

```
frontend/   React 19 + Vite + TypeScript + MapLibre
backend/    FastAPI + SQLAlchemy 2 + RQ + rasterio
database/   init de PostGIS, esquemas y AOIs de ejemplo
docs/       arquitectura, base de datos, API, pipeline y fuentes
storage/    archivos locales temporales (.gitkeep)
```

## Puesta en marcha

```bash
cp .env.example .env          # ajusta credenciales si hace falta
docker compose up -d database redis minio
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python scripts/seed_locations.py
docker compose up -d backend worker frontend
```

- API: <http://localhost:8000/docs>
- Frontend: <http://localhost:5173>
- Almacén de objetos: S3 en <http://localhost:9000> (VersityGW en desarrollo,
  bucket `spaceapps-data`; no hay consola web)

Verificación rápida:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/locations
```

## Tests

```bash
docker compose run --rm backend pytest
```

Los tests de integración que necesitan base de datos se saltan solos si
`DATABASE_URL` no está definida (dentro de Docker sí lo está).

`backend` y `worker` son imágenes distintas: tras cambiar dependencias del
backend, reconstruye ambas (`docker compose build backend worker`).

## Estado actual

Implementado: esquema completo, catálogo, AOIs, validación de pares, cola,
pipeline GCOV (diferencia → polígonos → métricas → COG), evidencia USGS,
endpoints de lectura y mapa.

No implementado a propósito: alineación/remuestreo, GUNW/GOFF/SME2, tiles XYZ
(responde 501), FIRMS/GPM. Ver `docs/architecture.md`.
