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

| Fuente | Tipo | Clave | Qué aporta |
|---|---|---|---|
| USGS FDSN | `EARTHQUAKE` | no | sismos M ≥ 3 (punto, magnitud) |
| NASA FIRMS | `FIRE` | `FIRMS_API_KEY` (gratis) | focos activos VIIRS de 375 m (punto, FRP en MW, confianza) |
| NASA POWER | `PRECIPITATION` | no | lluvia acumulada por celda de 0,5° × 0,625° y su anomalía frente a la climatología |

El análisis las consulta solo (paso `EVIDENCE_ANALYSIS`) para el intervalo entre las
dos adquisiciones y la zona donde hubo cambios. Una fuente que falla o no está
configurada no hace fallar el análisis: queda anotada en `job.result.evidence_sources`
para que la interfaz pueda distinguir "no hubo eventos" de "no se pudo consultar".
`fetch_auxiliary: false` en la petición
lo desactiva.

Las mismas fuentes se pueden consultar directamente para cualquier punto con las
rutas `/context/*` (ver `docs/api.md`).

- **FIRMS**: la clave se pide en <https://firms.modaps.eosdis.nasa.gov/api/map_key/> y
  va en `.env` como `FIRMS_API_KEY`. Se consultan las colecciones VIIRS NRT de
  NOAA-21, NOAA-20 y Suomi NPP (últimos ~2 meses) y, si no devuelven nada, las de
  archivo (`_SP`). Suomi NPP dejó de entregar datos el 2 de noviembre de 2026: se
  mantiene para fechas anteriores, y una colección que falle no descarta las demás.
- **POWER**: una consulta por celda, hasta 6 celdas (las que concentran más área
  cambiada). Cada ventana produce **un** evento cuya `magnitude` son los mm
  acumulados; `metadata` trae la serie diaria, lo esperado y `anomaly_pct`.
- `gpm_client.py` sigue como contrato: POWER entrega la misma magnitud ya agregada.

### Ventanas por tipo de evento (`evidence/profiles.py`)

El cambio ocurrió en algún momento entre las dos adquisiciones, así que la ventana de
referencia es `[antes, después]`; cada fenómeno añade su alcance y su antelación:

| Tipo | Radio | Antelación antes de la 1.ª fecha | Vínculos por cambio |
|---|---|---|---|
| `EARTHQUAKE` | 50 km | 1 día | 5 |
| `FIRE` | 2 km | 5 días | 10 |
| `PRECIPITATION` | la celda | 7 días | 1 |

`evidence_score = espacial × temporal × fuerza`: espacial cae de 1 a 0 con la
distancia hasta el radio; temporal vale 1 dentro del intervalo y cae a 0 a lo largo
de la antelación (un evento posterior a la 2.ª fecha vale 0); fuerza mide lo notable
del evento (magnitud, confianza del foco, lluvia y su anomalía).

### Tipo de cambio tentativo (`evidence/classification.py`)

| `change_type` | Regla |
|---|---|
| `POSSIBLE_BURN_SCAR` | focos FIRMS dentro o junto al área (confianza media si además bajó la retrodispersión) |
| `POSSIBLE_FLOODING` | cayó a nivel de agua abierta (< −17 dB co-pol, < −24 dB cross-pol) desde terreno; confianza media si la lluvia fue claramente anómala |
| `POSSIBLE_FLOODING` (confianza baja) | cayó ≥ 3 dB con lluvia anómala sin llegar a nivel de agua: inundación parcial |
| `POSSIBLE_FLOODED_VEGETATION` | subió ≥ 2 dB con lluvia anómala (rebote doble bajo vegetación) |
| `POSSIBLE_WATER_RECESSION` | tenía firma de agua y dejó de tenerla |
| `POSSIBLE_VEGETATION_LOSS` | bajó ≥ 2 dB desde vegetación densa, sin focos de fuego |
| `POSSIBLE_SEISMIC_DISTURBANCE` | sismo M ≥ 5 cercano en el intervalo |
| `UNCLASSIFIED` | ninguna regla encaja |

Todas son hipótesis (`POSSIBLE_`), nunca interpretaciones validadas.

## Datos de ejemplo

`database/seeds/locations.geojson` contiene cuatro AOI **aproximados** (Petén,
valle de Aconcagua, trapecio amazónico y delta del Krishna). No son límites administrativos y no
deben usarse para reportar superficies oficiales.

## Limitaciones que la interfaz debe declarar

1. Los valores de `change_score` y `evidence_score` son heurísticas no
   calibradas.
2. La coincidencia espacial y temporal con un evento auxiliar es contexto, no
   causalidad demostrada.
3. La detección GCOV mide el cambio de retrodispersión; el tipo de cambio es una
   hipótesis `POSSIBLE_*` derivada de reglas, no una clasificación validada.
4. Un par con distinta grilla no se procesa: falla con un error explícito antes
   de producir números incorrectos.
