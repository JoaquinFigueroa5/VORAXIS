"""Tentative change type from the radar signature plus the linked evidence.

Every label starts with POSSIBLE_: a backscatter change with a matching event
nearby is a hypothesis, not a validated interpretation. Without a rule that
fits, the change stays UNCLASSIFIED rather than being forced into a category.

Typical L-band backscatter (dB) used by the rules:

    open calm water      below -17 (co-pol)  / -24 (cross-pol)
    dense vegetation     above -10 (co-pol)  / -16 (cross-pol)
"""

from dataclasses import dataclass, field
from typing import Any

UNCLASSIFIED = "UNCLASSIFIED"

LABELS_ES = {
    "POSSIBLE_BURN_SCAR": "Posible área quemada",
    "POSSIBLE_FLOODING": "Posible inundación",
    "POSSIBLE_FLOODED_VEGETATION": "Posible vegetación inundada",
    "POSSIBLE_WATER_RECESSION": "Posible retroceso de agua",
    "POSSIBLE_VEGETATION_LOSS": "Posible pérdida de vegetación",
    "POSSIBLE_SEISMIC_DISTURBANCE": "Posible alteración por sismo",
    UNCLASSIFIED: "Cambio sin clasificar",
}

_WATER_DB = {"co": -17.0, "cross": -24.0}
_VEGETATION_DB = {"co": -10.0, "cross": -16.0}
# About 1 km from a confident detection inside the interval; farther is another fire.
_MIN_FIRE_SCORE = 0.4
_MIN_QUAKE_MAGNITUDE = 5.0
# Rain supports a flood hypothesis when it is clearly above normal, or extreme by itself.
_HEAVY_RAIN_MM = 50.0
_HEAVY_RAIN_ANOMALY_PCT = 50.0
_EXTREME_RAIN_MM = 200.0


@dataclass
class Classification:
    change_type: str = UNCLASSIFIED
    confidence: str = "NONE"  # NONE | LOW | MEDIUM
    reasons: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return LABELS_ES.get(self.change_type, self.change_type)


def _best(evidence: list[dict[str, Any]], event_type: str) -> dict[str, Any] | None:
    matches = [item for item in evidence if item.get("event_type") == event_type]
    return max(matches, key=lambda item: item.get("score") or 0.0) if matches else None


def classify(
    *,
    direction: str,
    mean_change_db: float,
    before_db: float,
    after_db: float,
    polarization: str = "HH",
    evidence: list[dict[str, Any]] | None = None,
) -> Classification:
    """`evidence` items: {event_type, score, magnitude, metadata}."""
    evidence = evidence or []
    kind = "co" if polarization[:1] == polarization[1:2] else "cross"
    water, vegetation = _WATER_DB[kind], _VEGETATION_DB[kind]
    decrease = direction == "DECREASE"
    change = abs(mean_change_db)

    fire = _best(evidence, "FIRE")
    rain = _best(evidence, "PRECIPITATION")
    quake = _best(evidence, "EARTHQUAKE")
    fire_count = sum(1 for item in evidence if item.get("event_type") == "FIRE")
    rain_meta = (rain or {}).get("metadata") or {}
    rain_mm = float(rain_meta.get("total_mm") or (rain or {}).get("magnitude") or 0.0)
    rain_anomaly = rain_meta.get("anomaly_pct")
    heavy_rain = rain is not None and (
        rain_mm >= _EXTREME_RAIN_MM
        or (rain_mm >= _HEAVY_RAIN_MM and (rain_anomaly or 0.0) >= _HEAVY_RAIN_ANOMALY_PCT)
    )
    rain_text = f"llovieron {rain_mm:.0f} mm en la ventana" + (
        f" ({rain_anomaly:+.0f} % respecto a lo normal)" if rain_anomaly is not None else ""
    )

    if fire is not None and (fire.get("score") or 0.0) >= _MIN_FIRE_SCORE:
        reasons = [
            f"{fire_count} detección(es) de fuego activo de FIRMS dentro o junto al área, "
            "entre las dos adquisiciones o pocos días antes."
        ]
        if decrease:
            reasons.append(
                f"La retrodispersión bajó {change:.1f} dB, lo esperado cuando se pierde vegetación al quemarse."
            )
            confidence = "MEDIUM" if (fire.get("score") or 0.0) >= 0.6 else "LOW"
        else:
            reasons.append(
                f"La retrodispersión subió {change:.1f} dB, lo que no es la firma habitual de un "
                "área quemada; la coincidencia con el fuego se mantiene como hipótesis débil."
            )
            confidence = "LOW"
        return Classification("POSSIBLE_BURN_SCAR", confidence, reasons)

    if decrease and after_db <= water and before_db > water + 2.0:
        reasons = [
            f"La retrodispersión cayó de {before_db:.1f} a {after_db:.1f} dB, un nivel propio de "
            "agua abierta en calma: la superficie pasó de terreno a espejo de agua."
        ]
        if heavy_rain:
            reasons.append(f"En la celda de la zona {rain_text}.")
        else:
            reasons.append("No hay lluvia notable registrada que lo respalde.")
        return Classification("POSSIBLE_FLOODING", "MEDIUM" if heavy_rain else "LOW", reasons)

    if decrease and heavy_rain and change >= 3.0 and before_db > water + 2.0:
        return Classification(
            "POSSIBLE_FLOODING",
            "LOW",
            [
                f"La retrodispersión cayó {change:.1f} dB (de {before_db:.1f} a {after_db:.1f} dB) sin "
                "llegar al nivel de agua abierta: es compatible con inundación parcial o cultivos "
                "anegados dentro del píxel.",
                f"En la celda de la zona {rain_text}.",
            ],
        )

    if not decrease and heavy_rain and change >= 2.0 and before_db > water:
        return Classification(
            "POSSIBLE_FLOODED_VEGETATION",
            "LOW",
            [
                f"La retrodispersión subió {change:.1f} dB: agua bajo vegetación refuerza el rebote "
                "doble de la señal en banda L.",
                f"En la celda de la zona {rain_text}.",
            ],
        )

    if not decrease and before_db <= water and after_db > water + 2.0:
        return Classification(
            "POSSIBLE_WATER_RECESSION",
            "LOW",
            [
                f"La retrodispersión subió de {before_db:.1f} a {after_db:.1f} dB: una superficie con "
                "firma de agua en la primera fecha ya no la tiene en la segunda."
            ],
        )

    if decrease and before_db >= vegetation and change >= 2.0 and after_db > water:
        return Classification(
            "POSSIBLE_VEGETATION_LOSS",
            "LOW",
            [
                f"La retrodispersión bajó {change:.1f} dB desde {before_db:.1f} dB, un nivel propio de "
                "vegetación densa, sin llegar a firma de agua.",
                "No hay detecciones de fuego cercanas: es compatible con tala o cosecha, no con quema.",
            ],
        )

    if (
        quake is not None
        and (quake.get("magnitude") or 0.0) >= _MIN_QUAKE_MAGNITUDE
        and (quake.get("score") or 0.0) >= 0.1
    ):
        return Classification(
            "POSSIBLE_SEISMIC_DISTURBANCE",
            "LOW",
            [
                f"Sismo de magnitud {quake['magnitude']:.1f} registrado por USGS cerca del área "
                "entre las dos adquisiciones.",
                "La retrodispersión no mide desplazamiento del terreno; confirmar con interferometría (GUNW).",
            ],
        )

    reasons = [
        f"Cambio de {mean_change_db:+.1f} dB ({before_db:.1f} → {after_db:.1f} dB) sin una firma "
        "ni un evento asociado que permita proponer una causa."
    ]
    return Classification(UNCLASSIFIED, "NONE", reasons)
