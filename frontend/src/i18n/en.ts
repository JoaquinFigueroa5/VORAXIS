import type { es } from "./es";

/** English copy. The type below fails the build if a key from `es.ts` is missing. */
export const en: Record<keyof typeof es, string> = {
  // --- shell ---------------------------------------------------------------
  "shell.skip": "Skip to content",
  "shell.brand_home": "Voraxis, home",
  "shell.sections": "Sections",
  "shell.nav.analysis": "Analysis",
  "shell.nav.explore": "Explore",
  "shell.nav.insights": "Insights",
  "shell.nav.methodology": "Methodology",
  "shell.language": "Language",
  "shell.mode.scientific": "Scientific mode",
  "shell.mode.explore": "Explore mode",
  "shell.mode.scientific.title": "Hide decibels, thresholds and processing metadata",
  "shell.mode.explore.title": "Show decibels, thresholds and processing metadata",
  "shell.footer.title": "Create a change analysis for your area",
  "shell.footer.subtitle":
    "NISAR imagery is public. Each date takes a few minutes to download the first time.",
  "shell.footer.cta": "Create an analysis",
  "shell.footer.saved": "Saved analyses",
  "shell.footer.new": "New analysis",
  "shell.footer.methodology": "Methodology and sources",
  "shell.footer.legal":
    "Radar: NISAR (NASA and ISRO), distributed by ASF DAAC. Rain: NASA POWER. Fires: NASA FIRMS. Earthquakes: USGS. Basemap: Esri, HERE, Garmin, © OpenStreetMap.",
  "shell.footer.legal_aria": "Data sources",

  // --- units and shared values --------------------------------------------
  "unit.km2": "km²",
  "unit.ha": "ha",
  "unit.db": "dB",
  "unit.percent": "%",
  "unit.pixels": "pixels",
  "unit.fraction": "fraction",
  "unit.amplitude": "amplitude",
  "unit.sigma": "σ",
  "value.no_data": "no data",
  "value.no_date": "no date",
  "value.no_region": "Change without a region",
  "action.close": "Close",
  "action.cancel": "Cancel",
  "action.retry": "Try again",
  "error.unexpected": "Something went wrong.",

  // --- change types --------------------------------------------------------
  "changeType.POSSIBLE_FLOODING.label": "Possible flooding",
  "changeType.POSSIBLE_FLOODING.reading":
    "The surface darkened for the radar. Calm water reflects the signal away from the satellite, so flooded ground looks darker.",
  "changeType.POSSIBLE_FLOODED_VEGETATION.label": "Possible flooded vegetation",
  "changeType.POSSIBLE_FLOODED_VEGETATION.reading":
    "The surface brightened after anomalous rain. Water under vegetation bounces the signal twice (water and stems) and returns it stronger.",
  "changeType.POSSIBLE_BURN_SCAR.label": "Possible burn scar",
  "changeType.POSSIBLE_BURN_SCAR.reading":
    "There are active fires next to the area during the interval. When vegetation burns, the radar signal usually drops.",
  "changeType.POSSIBLE_VEGETATION_LOSS.label": "Possible vegetation loss",
  "changeType.POSSIBLE_VEGETATION_LOSS.reading":
    "The signal dropped from a level typical of dense vegetation, with no nearby fire and no water signature. It is compatible with logging or harvest.",
  "changeType.POSSIBLE_WATER_RECESSION.label": "Possible water recession",
  "changeType.POSSIBLE_WATER_RECESSION.reading":
    "A surface that had a water signature on the first date no longer has it on the second.",
  "changeType.POSSIBLE_SEISMIC_DISTURBANCE.label": "Possible seismic disturbance",
  "changeType.POSSIBLE_SEISMIC_DISTURBANCE.reading":
    "A strong earthquake happened nearby during the interval. This measure does not detect ground displacement; it is only a coincidence to review.",
  "changeType.UNCLASSIFIED.label": "Unclassified change",
  "changeType.UNCLASSIFIED.reading":
    "The signal changed, but neither its signature nor nearby events suggest a cause.",

  // --- classification reasons ---------------------------------------------
  "reason.fire.nearby":
    "{count} FIRMS active-fire detection(s) inside or next to the area, between the two acquisitions or a few days before.",
  "reason.fire.decrease":
    "Backscatter dropped {delta} dB, which is expected when vegetation is lost to burning.",
  "reason.fire.increase":
    "Backscatter rose {delta} dB, which is not the usual signature of a burn scar; the match with the fire stays a weak hypothesis.",
  "reason.flood.open_water":
    "Backscatter fell from {before} to {after} dB, a level typical of open calm water: the surface went from ground to a water mirror.",
  "reason.rain.window": "In the area's grid cell, {mm} mm of rain fell during the window.",
  "reason.rain.window_anomaly":
    "In the area's grid cell, {mm} mm of rain fell during the window ({anomaly} % versus normal).",
  "reason.rain.none": "No significant recorded rain supports it.",
  "reason.flood.partial":
    "Backscatter fell {delta} dB (from {before} to {after} dB) without reaching the open-water level: it is compatible with partial flooding or waterlogged crops inside the pixel.",
  "reason.flooded_vegetation.increase":
    "Backscatter rose {delta} dB: water under vegetation strengthens the double bounce of the L-band signal.",
  "reason.water.recession":
    "Backscatter rose from {before} to {after} dB: a surface with a water signature on the first date no longer has it on the second.",
  "reason.vegetation.loss":
    "Backscatter dropped {delta} dB from {before} dB, a level typical of dense vegetation, without reaching a water signature.",
  "reason.vegetation.no_fire":
    "There are no nearby fire detections: it is compatible with logging or harvest, not with burning.",
  "reason.quake.nearby":
    "Magnitude {magnitude} earthquake recorded by USGS near the area between the two acquisitions.",
  "reason.quake.not_displacement":
    "Backscatter does not measure ground displacement; confirm with interferometry (GUNW).",
  "reason.unclassified":
    "A change of {delta} dB ({before} dB → {after} dB) with no signature or associated event that suggests a cause.",
  "confidence.NONE": "No confidence",
  "confidence.LOW": "Low confidence",
  "confidence.MEDIUM": "Medium confidence",

  // --- interpretation limitations -----------------------------------------
  "limitation.tentative":
    "The classification is tentative: `POSSIBLE_*` is a hypothesis compatible with the signal, not a confirmed diagnosis.",
  "limitation.causality": "Matching in space and time does not prove causation.",
  "limitation.score_not_probability":
    "The change_score measures the relative strength of the change in the signal; it is not a calibrated probability.",
  "limitation.source.unavailable": "{source} could not be queried.",
  "limitation.source.not_configured": "{source} is not configured: that context is missing.",
  "limitation.same_date": "Both acquisitions have the same date: there is no interval.",

  // --- external sources ----------------------------------------------------
  "source.NISAR": "NISAR · synthetic aperture radar",
  "source.USGS": "USGS · earthquake catalogue",
  "source.FIRMS": "NASA FIRMS · heat detections",
  "source.POWER": "NASA POWER · precipitation",
  "source.ASF": "ASF DAAC · NISAR catalogue",

  // --- metric names --------------------------------------------------------
  "metric.mean_change_db": "Mean backscatter change",
  "metric.mean_backscatter_before_db": "Backscatter before",
  "metric.mean_backscatter_after_db": "Backscatter after",
  "metric.peak_change_db": "Peak change",
  "metric.scene_baseline_shift_db": "Baseline shift",
  "metric.detection_threshold_db": "Detection threshold",
  "metric.mean_absolute_difference": "Mean difference (amplitude)",
  "metric.std_absolute_difference": "Difference deviation",
  "metric.changed_area_km2": "Changed area",
  "metric.changed_pixel_fraction": "Changed pixel fraction",
  "metric.valid_pixel_percentage": "Valid pixels",
  "metric.changed_pixel_count": "Changed pixels",
  "metric.job_changed_pixel_fraction": "Changed pixel fraction",
  "metric.job_valid_pixel_percentage": "Valid pixels of the job",
  "metric.threshold_sigma": "Detection threshold",

  // --- API errors ----------------------------------------------------------
  "api.error.generic": "We could not complete the operation.",
  "api.error.not_found": "We could not find what you asked for.",
  "api.error.conflict": "That action is not possible right now.",
  "api.error.bad_request": "Check the data you sent.",
  "api.error.validation_failed": "Check the data you sent: some fields are invalid.",
  "api.error.observations_incompatible":
    "The two dates cannot be compared. Check the details of the interval.",
  "api.error.processing_failed": "The processing failed.",
  "api.error.upstream_failed": "An external catalogue did not answer.",
  "api.error.upstream_unavailable": "{source} did not answer.",
  "api.error.upstream_not_configured": "{source} is not configured in the backend.",
  "api.error.not_implemented": "This feature is not available yet.",
  "api.error.queue_unavailable": "The job queue is not available.",
  "api.error.job_not_cancellable": "That job already finished and cannot be cancelled.",
  "api.error.location_name_taken": "An area named “{name}” already exists.",
  "api.error.location_name_blank": "Give the area a name.",
  "api.error.location_too_small": "The area is too small: each side must be at least {min} degrees.",
  "api.error.location_too_large":
    "The area spans {width} × {height} degrees; the maximum is {max} per side. Draw a smaller area.",
  "api.error.not_a_granule": "“{product_id}” is not a NISAR granule name.",
  "api.error.not_gcov": "{product_id} is a {product_type} product; only GCOV can be ingested.",
  "api.error.earthdata_not_configured":
    "Downloads need Earthdata credentials: set EARTHDATA_USERNAME and EARTHDATA_PASSWORD in .env.",
  "api.incompatible.same_observation": "You picked the same date twice.",
  "api.incompatible.dates_not_increasing": "The start date must come before the end date.",
  "api.incompatible.product_type_differs":
    "The products have different types ({before} and {after}).",
  "api.incompatible.maturity_differs": "The products have different maturity.",
  "api.incompatible.no_common_polarisation": "The two scenes share no polarisation.",
  "api.incompatible.scene_without_overlap": "Scene {product_id} does not cover the chosen area.",

  // --- job status and steps ------------------------------------------------
  "status.PENDING": "Queued",
  "status.QUEUED": "Queued",
  "status.RUNNING": "Running",
  "status.COMPLETED": "Completed",
  "status.FAILED": "Failed",
  "status.CANCELLED": "Cancelled",
  "step.QUEUED": "Queued",
  "step.PREPARING": "Preparing data",
  "step.DIFFERENCING": "Computing differences",
  "step.SEGMENTING": "Delineating areas",
  "step.VECTORIZING": "Vectorising changes",
  "step.CONTEXT": "Looking up context",
  "step.EVIDENCE": "Linking evidence",
  "step.EXPORTING": "Exporting layers",
  "step.DONE": "Done",
  "step.DOWNLOADING": "Downloading",
  "step.CONVERTING": "Converting",
  "step.UPLOADING": "Uploading",
  "step.READY": "Ready",
  "job.error.cancelled_by_user": "You cancelled the analysis.",
  "job.error.job_missing_rows": "The analysis lost data it needed.",
  "job.error.not_implemented": "That step is not implemented yet.",
  "job.error.generic": "The analysis stopped without giving a reason.",
  "job.warning.processing_version_differs":
    "The two dates were processed with different software versions ({before} and {after}); a small scene-wide offset between them is possible and is removed as the baseline.",
  "ingest.downloaded": "{done} of {total} GB",
  "ingest.downloaded_partial": "{done} GB downloaded",
};
