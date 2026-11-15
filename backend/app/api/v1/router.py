from fastapi import APIRouter

from app.api.v1.endpoints import (
    analysis,
    auxiliary,
    changes,
    context,
    evidence,
    health,
    ingest,
    insights,
    jobs,
    locations,
    nisar,
    observations,
    tiles,
)

router = APIRouter()
router.include_router(health.router)
router.include_router(locations.router)
router.include_router(nisar.router)
router.include_router(observations.router)
router.include_router(ingest.router)
router.include_router(analysis.router)
router.include_router(jobs.router)
router.include_router(changes.router)
router.include_router(tiles.router)
router.include_router(evidence.router)
router.include_router(auxiliary.router)
router.include_router(context.router)
router.include_router(insights.router)
