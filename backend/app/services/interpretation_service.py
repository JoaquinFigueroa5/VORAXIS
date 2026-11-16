"""One change, explained from what was actually measured.

Nothing new is inferred here: it gathers the stored classification, the
per-polygon metrics and the evidence already linked to the change, then says
which sources could not be checked. Whatever the pipeline never recorded stays
absent instead of being guessed.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.evidence.classification import UNCLASSIFIED
from app.models.location import Location
from app.models.observation import Observation
from app.models.processing_job import ProcessingJob
from app.repositories.observation_repository import ObservationRepository
from app.services.change_service import ChangeService
from app.services.evidence_service import EvidenceService


def _source_state(report: dict[str, Any] | None) -> dict[str, Any]:
    """`job.result.evidence_sources` as the three states the interface draws."""
    if not report:
        return {}
    status = report.get("status")
    state = {"ok": "AVAILABLE", "error": "UNAVAILABLE", "skipped": "NOT_CONFIGURED"}.get(
        status, "UNAVAILABLE"
    )
    return {
        "status": state,
        "events_found": report.get("events_found"),
        "detail": report.get("detail"),
        "code": {
            "UNAVAILABLE": "source.unavailable",
            "NOT_CONFIGURED": "source.not_configured",
        }.get(state),
    }


class InterpretationService:
    def __init__(
        self,
        changes: ChangeService | None = None,
        evidence: EvidenceService | None = None,
        observations: ObservationRepository | None = None,
    ) -> None:
        self.changes = changes or ChangeService()
        self.evidence = evidence or EvidenceService()
        self.observations = observations or ObservationRepository()

    def for_change(self, db: Session, change_id) -> dict[str, Any]:
        change = self.changes.get(db, change_id)
        job = db.get(ProcessingJob, change.job_id)
        if job is None:
            raise NotFoundError(f"job {change.job_id} not found")

        before = self.observations.get(db, job.before_observation_id)
        after = self.observations.get(db, job.after_observation_id)
        location = db.get(Location, job.location_id) if job.location_id else None

        classification = change.classification or {}
        reasons = classification.get("reasons") or []
        evidence = self.evidence.for_change(db, change_id)

        sources = {
            "NISAR": {
                "status": "AVAILABLE",
                "events_found": None,
                "detail": None,
                "code": None,
            }
        }
        for name, report in ((job.result or {}).get("evidence_sources") or {}).items():
            sources[name] = _source_state(report)

        limitations = [{"code": "tentative"}, {"code": "causality"}]
        if change.change_score is not None:
            limitations.append({"code": "score_not_probability"})
        for name, state in sources.items():
            if state["status"] == "UNAVAILABLE":
                limitations.append({"code": "source.unavailable", "params": {"source": name}})
            elif state["status"] == "NOT_CONFIGURED":
                limitations.append({"code": "source.not_configured", "params": {"source": name}})
        if before and after and after.acquisition_date == before.acquisition_date:
            limitations.append({"code": "same_date"})

        missing = [name for name, state in sources.items() if state["status"] != "AVAILABLE"]
        complete = not missing and change.change_type != UNCLASSIFIED

        return {
            "change_id": change.id,
            "job_id": change.job_id,
            "status": "COMPLETE" if complete else "PARTIAL",
            "location": (
                {"id": location.id, "name": location.name, "country": location.country}
                if location
                else None
            ),
            "period": {
                "before": before.acquisition_date if before else None,
                "after": after.acquisition_date if after else None,
                "interval_days": (
                    (after.acquisition_date - before.acquisition_date).total_seconds() / 86400.0
                    if before and after
                    else None
                ),
            },
            "observation": {
                "product_id": before.product_id if before else None,
                "product_type": before.product_type if before else None,
                "maturity": before.maturity if before else None,
                "polarization": before.polarization if before else None,
                "orbit_direction": before.orbit_direction if before else None,
                "processing_version": before.processing_version if before else None,
            },
            "change": {
                "change_type": change.change_type,
                "area_km2": change.area_km2,
                "change_score": change.change_score,
                "valid_pixel_percentage": change.valid_pixel_percentage,
                "direction": change.direction,
                "mean_change_db": change.mean_change_db,
            },
            "classification": {
                "confidence": classification.get("confidence"),
                "reasons": reasons,
            },
            "metrics": [
                {
                    "name": metric.metric_name,
                    "value": metric.value,
                    "unit": metric.unit,
                }
                for metric in self.changes.metrics(db, change_id)
            ],
            "evidence": evidence,
            "sources": sources,
            "limitations": limitations,
        }
