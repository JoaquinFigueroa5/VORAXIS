from fastapi import APIRouter, status

from app.dependencies import DbSession
from app.schemas.analysis import AnalysisAccepted, AnalysisRequest
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])
service = AnalysisService()


@router.post("", response_model=AnalysisAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_analysis(request: AnalysisRequest, db: DbSession) -> AnalysisAccepted:
    """Validate the pair, persist the job and queue it. Never runs the pipeline inline."""
    return service.create(db, request)
