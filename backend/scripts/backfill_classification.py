"""Recompute `change_events.classification` from stored evidence — no network.

The classifier stopped writing prose: reasons are `{code, params}`. This rewrites
rows persisted by the older shape using the metrics and evidence already in the
database, so a real analysis does not need to be downloaded or re-run.

    docker compose exec backend python scripts/backfill_classification.py
"""

import sys
from collections import Counter

from sqlalchemy import select

from app.core.database import SessionLocal
from app.evidence import classification
from app.models.auxiliary_event import AuxiliaryEvent
from app.models.change_event import ChangeEvent
from app.models.change_metric import ChangeMetric
from app.models.evidence_record import EvidenceRecord


def _evidence(db, change_id) -> list[dict]:
    rows = db.execute(
        select(AuxiliaryEvent, EvidenceRecord.evidence_score).where(
            EvidenceRecord.change_event_id == change_id,
            EvidenceRecord.auxiliary_event_id == AuxiliaryEvent.id,
        )
    ).all()
    return [
        {
            "event_type": event.event_type,
            "score": score,
            "magnitude": event.magnitude,
            "metadata": event.extra_metadata,
        }
        for event, score in rows
    ]


def _metrics(db, change_id) -> tuple[dict[str, float], str]:
    rows = db.execute(
        select(ChangeMetric.metric_name, ChangeMetric.value, ChangeMetric.extra_metadata).where(
            ChangeMetric.change_event_id == change_id,
        )
    ).all()
    values = {
        name: value
        for name, value, _ in rows
        if name in ("mean_backscatter_before_db", "mean_backscatter_after_db")
        and value is not None
    }
    # The pipeline records the polarisation with every metric; it picks the dB thresholds.
    polarization = next(
        (meta.get("polarization") for _, _, meta in rows if meta and meta.get("polarization")),
        "HH",
    )
    return values, polarization


def main() -> int:
    counts: Counter[str] = Counter()
    skipped = 0
    with SessionLocal() as db:
        changes = db.execute(select(ChangeEvent)).scalars().all()
        for change in changes:
            if change.direction is None or change.mean_change_db is None:
                skipped += 1
                continue
            metrics, polarization = _metrics(db, change.id)
            before = metrics.get("mean_backscatter_before_db")
            after = metrics.get("mean_backscatter_after_db")
            if before is None or after is None:
                skipped += 1
                continue
            result = classification.classify(
                direction=change.direction,
                mean_change_db=change.mean_change_db,
                before_db=before,
                after_db=after,
                polarization=polarization,
                evidence=_evidence(db, change.id),
            )
            change.change_type = result.change_type
            change.classification = {
                "type": result.change_type,
                "confidence": result.confidence,
                "reasons": result.reasons,
            }
            counts[result.change_type] += 1
        db.commit()

    for name, count in counts.most_common():
        print(f"{name:32} {count}")
    print(f"skipped (no metrics or direction): {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
