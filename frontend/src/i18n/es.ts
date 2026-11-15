/**
 * Spanish copy. `en.ts` must define exactly the same keys: its type is
 * `Record<keyof typeof es, string>`, so a missing translation fails the build.
 */
export const es = {
  // --- shell ---------------------------------------------------------------
  "shell.skip": "Saltar al contenido",
  "shell.brand_home": "Voraxis, inicio",
  "shell.sections": "Secciones",
  "shell.nav.analysis": "Análisis",
  "shell.nav.explore": "Explorar",
  "shell.nav.insights": "Insights",
  "shell.nav.methodology": "Metodología",
  "shell.language": "Idioma",
  "shell.mode.scientific": "Modo científico",
  "shell.mode.explore": "Modo exploración",
  "shell.mode.scientific.title": "Ocultar decibelios, umbrales y metadatos de proceso",
  "shell.mode.explore.title": "Mostrar decibelios, umbrales y metadatos de proceso",
  "shell.footer.title": "Crea un análisis de cambio para tu zona",
  "shell.footer.subtitle":
    "Las imágenes de NISAR son públicas. Cada fecha tarda unos minutos en descargarse la primera vez.",
  "shell.footer.cta": "Crear un análisis",
  "shell.footer.saved": "Análisis guardados",
  "shell.footer.new": "Nuevo análisis",
  "shell.footer.methodology": "Metodología y fuentes",
  "shell.footer.legal":
    "Radar: NISAR (NASA e ISRO), distribuido por ASF DAAC. Lluvia: NASA POWER. Incendios: NASA FIRMS. Sismos: USGS. Mapa base: Esri, HERE, Garmin, © OpenStreetMap.",
  "shell.footer.legal_aria": "Fuentes de datos",

  // --- units and shared values --------------------------------------------
  "unit.km2": "km²",
  "unit.ha": "ha",
  "unit.db": "dB",
  "unit.percent": "%",
  "unit.pixels": "píxeles",
  "unit.fraction": "fracción",
  "unit.amplitude": "amplitud",
  "unit.sigma": "σ",
  "value.no_data": "sin dato",
  "value.no_date": "sin fecha",
  "value.no_region": "Cambio sin región",
  "action.close": "Cerrar",
  "action.cancel": "Cancelar",
  "action.retry": "Reintentar",
  "error.unexpected": "Ocurrió un error inesperado.",

  // --- change types --------------------------------------------------------
  "changeType.POSSIBLE_FLOODING.label": "Posible inundación",
  "changeType.POSSIBLE_FLOODING.reading":
    "La superficie se oscureció para el radar. El agua en calma refleja la señal lejos del satélite, así que el terreno anegado se ve más oscuro.",
  "changeType.POSSIBLE_FLOODED_VEGETATION.label": "Posible vegetación inundada",
  "changeType.POSSIBLE_FLOODED_VEGETATION.reading":
    "La superficie se aclaró tras lluvia anómala. Agua bajo vegetación hace rebotar la señal dos veces (agua y tallos) y la devuelve con más fuerza.",
  "changeType.POSSIBLE_BURN_SCAR.label": "Posible área quemada",
  "changeType.POSSIBLE_BURN_SCAR.reading":
    "Hay focos de fuego activo junto al área en el intervalo. Al quemarse la vegetación, la señal de radar suele bajar.",
  "changeType.POSSIBLE_VEGETATION_LOSS.label": "Posible pérdida de vegetación",
  "changeType.POSSIBLE_VEGETATION_LOSS.reading":
    "La señal bajó desde un nivel propio de vegetación densa, sin fuego cercano ni firma de agua. Es compatible con tala o cosecha.",
  "changeType.POSSIBLE_WATER_RECESSION.label": "Posible retroceso de agua",
  "changeType.POSSIBLE_WATER_RECESSION.reading":
    "Una superficie que tenía firma de agua en la primera fecha dejó de tenerla en la segunda.",
  "changeType.POSSIBLE_SEISMIC_DISTURBANCE.label": "Posible alteración por sismo",
  "changeType.POSSIBLE_SEISMIC_DISTURBANCE.reading":
    "Hubo un sismo fuerte cerca en el intervalo. Esta medida no mide desplazamiento del terreno; es solo una coincidencia a revisar.",
  "changeType.UNCLASSIFIED.label": "Cambio sin clasificar",
  "changeType.UNCLASSIFIED.reading":
    "La señal cambió, pero ni su firma ni los eventos cercanos permiten proponer una causa.",

  // --- classification reasons (backend sends {code, params}) ---------------
  "reason.fire.nearby":
    "{count} detección(es) de fuego activo de FIRMS dentro o junto al área, entre las dos adquisiciones o pocos días antes.",
  "reason.fire.decrease":
    "La retrodispersión bajó {delta} dB, lo esperado cuando se pierde vegetación al quemarse.",
  "reason.fire.increase":
    "La retrodispersión subió {delta} dB, lo que no es la firma habitual de un área quemada; la coincidencia con el fuego se mantiene como hipótesis débil.",
  "reason.flood.open_water":
    "La retrodispersión cayó de {before} a {after} dB, un nivel propio de agua abierta en calma: la superficie pasó de terreno a espejo de agua.",
  "reason.rain.window": "En la celda de la zona llovieron {mm} mm en la ventana.",
  "reason.rain.window_anomaly":
    "En la celda de la zona llovieron {mm} mm en la ventana ({anomaly} % respecto a lo normal).",
  "reason.rain.none": "No hay lluvia notable registrada que lo respalde.",
  "reason.flood.partial":
    "La retrodispersión cayó {delta} dB (de {before} a {after} dB) sin llegar al nivel de agua abierta: es compatible con inundación parcial o cultivos anegados dentro del píxel.",
  "reason.flooded_vegetation.increase":
    "La retrodispersión subió {delta} dB: agua bajo vegetación refuerza el rebote doble de la señal en banda L.",
  "reason.water.recession":
    "La retrodispersión subió de {before} a {after} dB: una superficie con firma de agua en la primera fecha ya no la tiene en la segunda.",
  "reason.vegetation.loss":
    "La retrodispersión bajó {delta} dB desde {before} dB, un nivel propio de vegetación densa, sin llegar a firma de agua.",
  "reason.vegetation.no_fire":
    "No hay detecciones de fuego cercanas: es compatible con tala o cosecha, no con quema.",
  "reason.quake.nearby":
    "Sismo de magnitud {magnitude} registrado por USGS cerca del área entre las dos adquisiciones.",
  "reason.quake.not_displacement":
    "La retrodispersión no mide desplazamiento del terreno; confirmar con interferometría (GUNW).",
  "reason.unclassified":
    "Cambio de {delta} dB ({before} dB → {after} dB) sin una firma ni un evento asociado que permita proponer una causa.",
  "confidence.NONE": "Sin confianza",
  "confidence.LOW": "Confianza baja",
  "confidence.MEDIUM": "Confianza media",

  // --- interpretation limitations -----------------------------------------
  "limitation.tentative":
    "La clasificación es tentativa: `POSSIBLE_*` es una hipótesis compatible con la señal, no un diagnóstico confirmado.",
  "limitation.causality": "Coincidir en el espacio y en el tiempo no demuestra causalidad.",
  "limitation.score_not_probability":
    "El change_score mide la intensidad relativa del cambio en la señal, no es una probabilidad calibrada.",
  "limitation.source.unavailable": "No se pudo consultar {source}.",
  "limitation.source.not_configured": "{source} no está configurado: ese contexto falta.",
  "limitation.same_date": "Las dos adquisiciones tienen la misma fecha: no hay intervalo.",

  // --- external sources ----------------------------------------------------
  "source.NISAR": "NISAR · radar de apertura sintética",
  "source.USGS": "USGS · catálogo sísmico",
  "source.FIRMS": "NASA FIRMS · focos de calor",
  "source.POWER": "NASA POWER · precipitación",
  "source.ASF": "ASF DAAC · catálogo NISAR",

  // --- metric names --------------------------------------------------------
  "metric.mean_change_db": "Cambio medio de retrodispersión",
  "metric.mean_backscatter_before_db": "Retrodispersión antes",
  "metric.mean_backscatter_after_db": "Retrodispersión después",
  "metric.peak_change_db": "Cambio máximo",
  "metric.scene_baseline_shift_db": "Desplazamiento de la línea base",
  "metric.detection_threshold_db": "Umbral de detección",
  "metric.mean_absolute_difference": "Diferencia media (amplitud)",
  "metric.std_absolute_difference": "Desviación de la diferencia",
  "metric.changed_area_km2": "Área modificada",
  "metric.changed_pixel_fraction": "Fracción de píxeles modificados",
  "metric.valid_pixel_percentage": "Píxeles válidos",
  "metric.changed_pixel_count": "Píxeles modificados",
  "metric.job_changed_pixel_fraction": "Fracción de píxeles modificados",
  "metric.job_valid_pixel_percentage": "Píxeles válidos del trabajo",
  "metric.threshold_sigma": "Umbral de detección",

  // --- API errors (backend sends a stable code) ---------------------------
  "api.error.generic": "No pudimos completar la operación.",
  "api.error.not_found": "No encontramos lo que pediste.",
  "api.error.conflict": "Esa acción no es posible en este momento.",
  "api.error.bad_request": "Revisa los datos enviados.",
  "api.error.validation_failed": "Revisa los datos enviados: hay campos inválidos.",
  "api.error.observations_incompatible":
    "Las dos fechas no se pueden comparar. Revisa los detalles del intervalo.",
  "api.error.processing_failed": "El procesamiento falló.",
  "api.error.upstream_failed": "Un catálogo externo no respondió.",
  "api.error.upstream_unavailable": "{source} no respondió.",
  "api.error.upstream_not_configured": "Falta configurar {source} en el backend.",
  "api.error.not_implemented": "Esta función todavía no está disponible.",
  "api.error.queue_unavailable": "La cola de trabajos no está disponible.",
  "api.error.job_not_cancellable": "Ese trabajo ya terminó y no se puede cancelar.",
  "api.error.location_name_taken": "Ya existe una zona con el nombre «{name}».",
  "api.error.location_name_blank": "Ponle un nombre a la zona.",
  "api.error.location_too_small": "La zona es muy pequeña: cada lado debe medir al menos {min} grados.",
  "api.error.location_too_large":
    "La zona abarca {width} × {height} grados; el máximo es {max} por lado. Dibuja un área más pequeña.",
  "api.error.not_a_granule": "«{product_id}» no es un nombre de gránulo NISAR.",
  "api.error.not_gcov": "{product_id} es un producto {product_type}; solo se puede ingerir GCOV.",
  "api.error.earthdata_not_configured":
    "Las descargas necesitan credenciales de Earthdata: configura EARTHDATA_USERNAME y EARTHDATA_PASSWORD en .env.",
  "api.incompatible.same_observation": "Elegiste la misma fecha dos veces.",
  "api.incompatible.dates_not_increasing": "La fecha inicial debe ser anterior a la final.",
  "api.incompatible.product_type_differs":
    "Los productos son de tipos distintos ({before} y {after}).",
  "api.incompatible.maturity_differs": "Los productos tienen distinta madurez.",
  "api.incompatible.no_common_polarisation": "Las dos escenas no comparten polarización.",
  "api.incompatible.scene_without_overlap": "La escena {product_id} no cubre la zona elegida.",

  // --- job status and steps -----------------------------------------------
  "status.PENDING": "En cola",
  "status.QUEUED": "En cola",
  "status.RUNNING": "En proceso",
  "status.COMPLETED": "Completado",
  "status.FAILED": "Falló",
  "status.CANCELLED": "Cancelado",
  "step.QUEUED": "En cola",
  "step.PREPARING": "Preparando datos",
  "step.DIFFERENCING": "Calculando diferencias",
  "step.SEGMENTING": "Delimitando áreas",
  "step.VECTORIZING": "Vectorizando cambios",
  "step.CONTEXT": "Buscando contexto",
  "step.EVIDENCE": "Vinculando evidencia",
  "step.EXPORTING": "Exportando capas",
  "step.DONE": "Terminado",
  "step.DOWNLOADING": "Descargando",
  "step.CONVERTING": "Convirtiendo",
  "step.UPLOADING": "Subiendo",
  "step.READY": "Listo",
  "job.error.cancelled_by_user": "Cancelaste el análisis.",
  "job.error.job_missing_rows": "El análisis perdió datos que necesitaba.",
  "job.error.not_implemented": "Ese paso todavía no está implementado.",
  "job.error.generic": "El análisis se detuvo sin dar un motivo.",
  "job.warning.processing_version_differs":
    "Las dos fechas se procesaron con versiones distintas del software ({before} y {after}); puede haber un pequeño desfase entre escenas que se corrige con la línea base.",
  "ingest.downloaded": "{done} de {total} GB",
  "ingest.downloaded_partial": "{done} GB descargados",
} as const;
