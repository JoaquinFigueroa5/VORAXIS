from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.evidence import AuxiliaryEventOut
from app.services.evidence_service import EvidenceService


class AuxiliaryService:
    """Thin facade kept separate because auxiliary ingestion is its own pipeline."""

    def __init__(self, evidence: EvidenceService | None = None) -> None:
        self.evidence = evidence or EvidenceService(EvidenceRepository())

    def list(self, db, **filters) -> list[AuxiliaryEventOut]:
        return self.evidence.list_auxiliary(db, **filters)
