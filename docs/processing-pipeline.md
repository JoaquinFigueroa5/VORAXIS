# Pipeline de procesamiento

`app/processing/pipeline.py` ejecuta pasos secuenciales, cada uno actualiza
`processing_jobs.progress` y `current_step`. El worker relee el trabajo antes de
cada paso, de modo que una cancelación surte efecto entre pasos.

| Paso | Módulo | Actual |
|---|---|---|
| `DOWNLOADING` | `download.py` | copia el raster `SOURCE` del almacén de objetos al workdir |
| `PREPROCESSING` | `preprocessing.py` | lee la banda de la polarización pedida, máscara de nodata |
| `ALIGNMENT` | `alignment.py` + `quality_control.py` | recorta ambas fechas a su intersección; % de píxeles válidos |
| `CHANGE_DETECTION` | `change_detection.py` + `algorithms/gcov.py` | log-ratio en dB con signo, umbral robusto |
| `VECTORIZATION` | `vectorization.py` + `metrics.py` | un polígono por región, con score y métricas propios |
| `EVIDENCE_ANALYSIS` | `evidence/engine.py` | relaciones espacio-temporales |
| `EXPORTING` | `raster_export.py` | COG de diferencia y máscara al almacén de objetos |

## Método de detección (GCOV)

1. **Banda**: se lee la polarización pedida (`HH` por defecto) buscándola en la
   descripción de las bandas del COG. Si no existe, el job falla diciendo cuáles hay.
2. **Log-ratio con signo**: `d = después_dB − antes_dB` (= `10·log10(después/antes)`).
   Negativo = la superficie se oscureció (agua abierta tras inundación, quemado,
   tala); positivo = se aclaró (vegetación inundada, estructuras, rebrote).
3. **Píxeles que no cuentan**: nodata, el borde de la pasada (`edge_buffer_pixels`,
   16 por defecto) y lo que está bajo el piso de ruido en *ambas* fechas
   (`noise_floor_db`, −30 dB: agua en calma, sombra). Oscuro en una sola fecha sí
   cuenta: eso es una inundación.
4. **Suavizado**: filtro de mediana (`smoothing_window`, 5 px) contra el speckle.
   Mediana y no promedio porque conserva los bordes de las áreas cambiadas.
5. **Línea base y umbral robustos**: la mediana de `d` es la línea base (un
   desplazamiento de toda la escena no es un cambio local). La dispersión sale de
   la MAD: `σ = 1.4826·MAD`, `umbral = max(k·σ, 1 dB)` con `k` =
   `change_threshold_sigma`. Se marca `|d − línea base| > umbral`.
6. Limpieza morfológica: apertura 3×3 y eliminación de componentes < 4 píxeles.
7. Cada región conexa se poligoniza, se reproyecta a EPSG:4326 y se descarta si
   mide menos de `minimum_area_km2` (0,01 km² por defecto). Área geodésica con
   `pyproj.Geod` (WGS84).

`change_score` es **por polígono**: `1 − umbral / media(|d − línea base|)` dentro
del polígono, acotado a [0, 1). Vale 0 en el umbral, 0,5 al doble y 0,75 al
cuádruple. Es una **intensidad relativa**, no una probabilidad.

## Requisitos de entrada

- Ambos rasters deben existir como `processing.raster_assets` con
  `asset_type = 'SOURCE'`, formato `TIFF` o `COG`.
- Misma CRS y misma resolución; si las grillas están desplazadas un número entero
  de píxeles se recortan a la intersección. Otra cosa falla con el motivo.
- Los COG ingeridos llevan la etiqueta `units=dB`; un raster sin ella se trata como
  potencia lineal y se convierte.
- Polarización y madurez compatibles (validado antes de encolar).

## Salidas

- `analysis.change_events`: geometría, `change_type = 'UNCLASSIFIED'`, área,
  `change_score` propio y % válido del job.
- `analysis.change_metrics`, por polígono: `mean_change_db`, `peak_change_db`,
  `mean_backscatter_before_db`, `mean_backscatter_after_db`, `changed_area_km2`,
  `changed_pixel_count`; y de la detección: `detection_threshold_db`,
  `scene_baseline_shift_db`, `job_changed_pixel_fraction`,
  `job_valid_pixel_percentage`. Cada métrica lleva en `metadata` la polarización y
  `direction` (`DECREASE` / `INCREASE`).
- Objetos S3 `jobs/{job_id}/difference.tif` (log-ratio en dB, nodata NaN) y
  `change_mask.tif`, ambos COG reales con overviews.

## Tiles para el mapa

`services/tile_service.py` dibuja tiles XYZ de 256 px (PNG, Web Mercator) leyendo
los COG, que se copian una vez a una caché local.

| Capa | Qué muestra |
|---|---|
| `before` / `after` | retrodispersión en gris, −22…−2 dB (co-pol) o −28…−8 dB (cross-pol) |
| `difference` | rojo = se oscureció, azul = se aclaró; transparente donde no hay cambio |
| `mask` | píxeles marcados como cambio, en naranja |

## Ingesta GCOV (HDF5 → COG → DB)

Paso previo al análisis: deja cada adquisición como `Observation` `READY` con su
raster `SOURCE`.

```
.h5 local  (o descarga con Earthdata desde nisar_scenes.source_url → backend/data/nisar/)
  → processing/ingest_gcov.py    recorte al bbox del AOI, potencia → dB, COG
  → S3  sources/{observation_id}/{product_id}.tif
  → services/ingest_service.py   catalog.observations (READY) + processing.raster_assets (SOURCE)
```

```bash
# Dentro de docker los archivos de backend/data/ se ven en /app/data/
python scripts/ingest_nisar.py inspect data/nisar/X.h5 --tree     # ver estructura real
python scripts/ingest_nisar.py convert data/nisar/X.h5 out.tif --bbox=-90.6,15.9,-89.0,17.8
python scripts/ingest_nisar.py ingest --file data/nisar/X.h5 --location "Petén"
python scripts/ingest_nisar.py ingest --product-id NISAR_L2_PR_GCOV_... --location "Petén"
python scripts/make_synthetic_gcov.py                              # par sintético de prueba
```

Como tarea RQ: `app.workers.queues.enqueue_ingest(location_id, h5_path=... | scene_id=... | product_id=...)`.

Decisiones:

- **Un solo COG multibanda por observación** (una banda por polarización, descrita
  `HH`, `HV`…). La banda 1 es la co-pol porque el pipeline lee la banda 1.
- **Valores en dB** (`10·log10`), `float32`, nodata = `NaN`. Píxeles ≤ 0, no finitos o
  iguales a `_FillValue` pasan a nodata, igual que la potencia por debajo de −50 dB
  (artefactos de borde, muy por debajo del ruido del radar). El COG lleva la etiqueta
  `units=dB`.
- **Grilla de salida = bbox del AOI ajustado al posting del producto**, rellenando con
  nodata donde el frame no cubre. Dos fechas del mismo track/frame ingeridas para el
  mismo AOI quedan en la misma grilla, que es lo que exige `alignment.py`.
  `metadata.frame_coverage` indica cuánto del AOI cubre el frame.
- `--multilook N` promedia N×N píxeles **en potencia** antes de pasar a dB (menos
  speckle y rasters más livianos). Ambas fechas de un par deben usar el mismo N.
- Si la escena no está en `catalog.nisar_scenes` se crea desde los metadatos del HDF5
  (`maturity` queda `NULL`). `processing_version` = CRID del nombre del gránulo.
- Idempotente: reingerir la misma escena+AOI no hace nada salvo `--force`. Si falla,
  la observación queda `FAILED`.
- Las rutas HDF5 están en `GcovLayout` (`ingest_gcov.py`). Se escribieron a partir de la
  especificación del producto y **aún no se han verificado contra un gránulo real**.
