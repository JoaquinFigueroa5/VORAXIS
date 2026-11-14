import uuid

from fastapi import APIRouter

from app.dependencies import DbSession
from app.schemas.evidence import EvidenceRecordOut
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/changes", tags=["evidence"])
service = EvidenceService()


@router.get("/{change_id}/evidence", response_model=list[EvidenceRecordOut])
def get_evidence(change_id: uuid.UUID, db: DbSession) -> list[EvidenceRecordOut]:
    return service.for_change(db, change_id)
