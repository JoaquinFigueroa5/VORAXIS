from fastapi import APIRouter

from app.dependencies import DbSession
from app.schemas.common import InsightsOut
from app.services.insights_service import InsightsService

router = APIRouter(prefix="/insights", tags=["insights"])
service = InsightsService()


@router.get("", response_model=InsightsOut)
def get_insights(db: DbSession) -> InsightsOut:
    return service.summary(db)
