# Fuentes de datos

## NISAR / ASF DAAC

- Búsqueda: `asf_search.geo_search(platform="NISAR", intersectsWith=<WKT>, start, end)`.
  No requiere credenciales.
- Descarga autenticada: Earthdata Login (`EARTHDATA_USERNAME`,
  `EARTHDATA_PASSWORD`). Sin credenciales, la sincronización de catálogo funciona
  y la descarga no.
- Productos contemplados: `GCOV`, `GUNW`, `GOFF`, `SME2`.
  Solo `GCOV` tiene algoritmo de cambio implementado.
- La madurez del producto se guarda tal como la reporta ASF y se exige igual en
  ambos lados del par. No se mezclan `PROVISIONAL` con `BETA`.

## Fuentes auxiliares

| Fuente | Tipo | Estado |
|---|---|---|
| USGS FDSN | `EARTHQUAKE` | implementado (sin API key) |
| NASA FIRMS | `FIRE` | contrato; requiere `FIRMS_API_KEY` |
| GPM IMERG | `PRECIPITATION` | contrato; requiere Earthdata |

Ingesta USGS:

```bash
docker compose exec backend python -c "
from app.workers.tasks.process_auxiliary import run
run('-90.6,15.9,-89.0,17.8', '2026-06-01', '2026-06-30', 3.0)
"
```

## Datos de ejemplo

`database/seeds/locations.geojson` contiene tres AOI **aproximados** (Petén,
valle de Aconcagua, trapecio amazónico). No son límites administrativos y no
deben usarse para reportar superficies oficiales.

## Limitaciones que la interfaz debe declarar

1. Los valores de `change_score` y `evidence_score` son heurísticas no
   calibradas.
2. La coincidencia espacial y temporal con un evento auxiliar es contexto, no
   causalidad demostrada.
3. La detección GCOV mide diferencia de amplitud; no distingue por sí sola
   inundación, incendio ni terremoto.
4. Un par con distinta grilla no se procesa: falla con un error explícito antes
   de producir números incorrectos.
