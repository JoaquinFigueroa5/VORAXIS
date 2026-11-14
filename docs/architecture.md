# Archivo de arquitectura

Monolito modular con procesamiento geoespacial asíncrono. No hay microservicios:
un backend FastAPI, un worker RQ que comparte el mismo código, PostGIS, Redis y
un almacén de objetos S3 (VersityGW en desarrollo; el servicio se llama `minio`
y el cliente es minio-py). El frontend consume REST + GeoJSON.

```
frontend (React/Vite) ──REST/GeoJSON──► backend (FastAPI)
                                          │  ├─ PostGIS (metadatos, vectores)
                                          │  ├─ Redis   (cola RQ)
                                          │  └─ S3      (HDF5/COG)
                                          ▼
                                       worker (RQ)
                                          └─ processing/ + evidence/
```

## Flujo de un análisis

1. `POST /api/v1/analysis` valida el par de observaciones y crea la fila en
   `processing.processing_jobs` con estado `PENDING`.
2. El endpoint encola `app.workers.tasks.analyze_job.run` en Redis y responde
   `202` con el `job_id`. Nunca procesa raster en la petición.
3. El worker ejecuta `app/processing/pipeline.py`: descarga los rasters fuente
   del almacén de objetos, valida calidad, alinea, detecta cambios, vectoriza,
   busca evidencia y exporta COGs.
4. El frontend consulta `GET /api/v1/jobs/{id}` con polling mientras el estado
   sea `PENDING` o `RUNNING`.

## Decisiones que se mantienen

1. **No mezclar madureces de producto.** `analysis_service.compatibility_problems`
   rechaza pares con distinta madurez, tipo de producto, versión de procesamiento
   o sin polarización común.
2. **No asumir comparabilidad por cercanía.** Además de lo anterior, cada huella
   debe intersectar el AOI (`ST_Intersects`).
3. **Nada de raster en PostgreSQL.** Los bytes viven en el almacén de objetos;
   `raster_assets` guarda únicamente la clave del objeto y metadatos.
4. **Ningún cambio se etiqueta como fenómeno.** `change_type` es `UNCLASSIFIED`
   hasta que exista una interpretación validada.
5. **Una fuente auxiliar real antes que tres incompletas.** USGS está
   implementado; FIRMS y GPM son contratos explícitos (`NotImplementedFeature`).

## Qué no está implementado todavía

- Re-muestreo/co-registro cuando los rasters no comparten grilla
  (`processing/alignment.py` falla con un mensaje claro).
- Algoritmos para GUNW, GOFF y SME2.
- Tiles XYZ (el endpoint responde `501`).
- Ingesta de FIRMS y GPM.

## Estados de un trabajo

`PENDING → RUNNING → COMPLETED | FAILED | CANCELLED`. La cancelación se aplica
entre pasos: el worker relee la fila antes de cada paso y se detiene si el estado
es `CANCELLED`.
