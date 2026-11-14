# Pipeline de procesamiento

`app/processing/pipeline.py` ejecuta pasos secuenciales, cada uno actualiza
`processing_jobs.progress` y `current_step`. El worker relee el trabajo antes de
cada paso, de modo que una cancelación surte efecto entre pasos.

| Paso | Módulo | Actual |
|---|---|---|
| `DOWNLOADING` | `download.py` | copia el raster `SOURCE` del almacén de objetos al workdir |
| `PREPROCESSING` | `preprocessing.py` | lee una banda, construye máscara de nodata |
| `ALIGNMENT` | `alignment.py` | exige misma grilla; si no, `NotImplementedError` |
| `QUALITY_CONTROL` | `quality_control.py` | % de píxeles válidos vs. parámetro |
| `CHANGE_DETECTION` | `change_detection.py` + `algorithms/gcov.py` | diferencia absoluta robusta |
| `VECTORIZATION` | `vectorization.py` + `metrics.py` | polígonos en 4326 y métricas |
| `EVIDENCE_ANALYSIS` | `evidence/engine.py` | relaciones espacio-temporales |
| `EXPORTING` | `raster_export.py` | COG de diferencia y máscara al almacén de objetos |

## Método de detección (GCOV)

1. Diferencia absoluta por píxel entre `before` y `after`.
2. `threshold = k · σ`, con `k` = `change_threshold_sigma` (por defecto 2).
3. Se marca lo que se aleja del **mediano** de la diferencia más que el umbral
   (robusto a que el área cambiada sea pequeña).
4. Limpieza morfológica: apertura 3×3 y eliminación de componentes < 4 píxeles.
5. Poligonización con `rasterio.features.shapes`, reproyección a EPSG:4326 y
   descarte de áreas < 1 000 m².
6. Área geodésica con `pyproj.Geod` (WGS84).

`change_score = media(|diferencia| en píxeles marcados) / threshold`, acotado a
[0, 1]. Es una **intensidad relativa**, no una probabilidad.

## Requisitos de entrada

- Ambos rasters deben existir como `processing.raster_assets` con
  `asset_type = 'SOURCE'`, formato `TIFF` o `COG`.
- Misma CRS, misma forma y misma transformación afín.
- Polarización y madurez compatibles (validado antes de encolar).

## Salidas

- `analysis.change_events` (geometría `UNCLASSIFIED`, área, score, % válido).
- `analysis.change_metrics`: `mean_absolute_difference`,
  `std_absolute_difference`, `threshold_sigma`, `changed_pixel_fraction`,
  `changed_area_km2`, `valid_pixel_percentage`.
- Objetos S3 `jobs/{job_id}/difference.tif` y `change_mask.tif` (`COG`).
