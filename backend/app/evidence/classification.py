"""Tentative change type from the radar signature plus the linked evidence.

Every type starts with POSSIBLE_: a backscatter change with a matching event
nearby is a hypothesis, not a validated interpretation. Without a rule that
fits, the change stays UNCLASSIFIED rather than being forced into a category.

Typical L-band backscatter (dB) used by the rules:

    open calm water      below -17 (co-pol)  / -24 (cross-pol)
    dense vegetation     above -10 (co-pol)  / -16 (cross-pol)

Reasons are `{code, params}`: the client writes the sentence in its language and
no prose is stored. Numbers arrive as strings with a dot decimal separator, which
reads the same in Spanish and English.
"""

from dataclasses import dataclass, field
from typing import Any

UNCLASSIFIED = "UNCLASSIFIED"

_WATER_DB = {"co": -17.0, "cross": -24.0}
_VEGETATION_DB = {"co": -10.0, "cross": -16.0}
# About 1 km from a confident detection inside the interval; farther is another fire.
_MIN_FIRE_SCORE = 0.4
_MIN_QUAKE_MAGNITUDE = 5.0
# Rain supports a flood hypothesis when it is clearly above normal, or extreme by itself.
_HEAVY_RAIN_MM = 50.0
_HEAVY_RAIN_ANOMALY_PCT = 50.0
_EXTREME_RAIN_MM = 200.0


def reason(code: str, **params: str) -> dict[str, Any]:
    return {"code": code, "params": params}


def _mm(value: float) -> str:
    return f"{value:.0f}"


def _db(value: float) -> str:
    return f"{value:.1f}"


def _signed_db(value: float) -> str:
    return f"{value:+.1f}"


def _pct(value: float) -> str:
    return f"{value:+.0f}"


@dataclass
class Classification:
    change_type: str = UNCLASSIFIED
    confidence: str = "NONE"  # NONE | LOW | MEDIUM
    reasons: list[dict[str, Any]] = field(default_factory=list)


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
    rain_reason = (
        reason("rain.window_anomaly", mm=_mm(rain_mm), anomaly=_pct(float(rain_anomaly)))
        if rain_anomaly is not None
        else reason("rain.window", mm=_mm(rain_mm))
    )

    if fire is not None and (fire.get("score") or 0.0) >= _MIN_FIRE_SCORE:
        reasons = [
            reason(
                "fire.nearby",
                count=str(fire_count),
            )
        ]
        if decrease:
            reasons.append(reason("fire.decrease", delta=_db(change)))
            confidence = "MEDIUM" if (fire.get("score") or 0.0) >= 0.6 else "LOW"
        else:
            reasons.append(reason("fire.increase", delta=_db(change)))
            confidence = "LOW"
        return Classification("POSSIBLE_BURN_SCAR", confidence, reasons)

    if decrease and after_db <= water and before_db > water + 2.0:
        reasons = [
            reason("flood.open_water", before=_db(before_db), after=_db(after_db)),
        ]
        reasons.append(rain_reason if heavy_rain else reason("rain.none"))
        return Classification("POSSIBLE_FLOODING", "MEDIUM" if heavy_rain else "LOW", reasons)

    if decrease and heavy_rain and change >= 3.0 and before_db > water + 2.0:
        return Classification(
            "POSSIBLE_FLOODING",
            "LOW",
            [
                reason(
                    "flood.partial",
                    delta=_db(change),
                    before=_db(before_db),
                    after=_db(after_db),
                ),
                rain_reason,
            ],
        )

    if not decrease and heavy_rain and change >= 2.0 and before_db > water:
        return Classification(
            "POSSIBLE_FLOODED_VEGETATION",
            "LOW",
            [reason("flooded_vegetation.increase", delta=_db(change)), rain_reason],
        )

    if not decrease and before_db <= water and after_db > water + 2.0:
        return Classification(
            "POSSIBLE_WATER_RECESSION",
            "LOW",
            [reason("water.recession", before=_db(before_db), after=_db(after_db))],
        )

    if decrease and before_db >= vegetation and change >= 2.0 and after_db > water:
        return Classification(
            "POSSIBLE_VEGETATION_LOSS",
            "LOW",
            [
                reason("vegetation.loss", delta=_db(change), before=_db(before_db)),
                reason("vegetation.no_fire"),
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
                reason("quake.nearby", magnitude=_db(float(quake["magnitude"]))),
                reason("quake.not_displacement"),
            ],
        )

    return Classification(
        UNCLASSIFIED,
        "NONE",
        [
            reason(
                "unclassified",
                delta=_signed_db(mean_change_db),
                before=_db(before_db),
                after=_db(after_db),
            )
        ],
    )
