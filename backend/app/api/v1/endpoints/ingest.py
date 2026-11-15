"""Ask for NISAR products to be downloaded and prepared, and follow the progress.

    POST /ingest            queue one task per product (202)
    GET  /ingest/{id}       status, stage and progress of a task
    GET  /ingest            queued, running and recent tasks

A finished task's `result.observation_id` is what POST /analysis needs.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.dependencies import DbSession
from app.schemas.ingest import IngestRequest, IngestTaskOut
from app.services.ingest_task_service import IngestTaskService

router = APIRouter(prefix="/ingest", tags=["ingest"])
service = IngestTaskService()


@router.post("", response_model=list[IngestTaskOut], status_code=status.HTTP_202_ACCEPTED)
def create_ingestion(request: IngestRequest, db: DbSession) -> list[IngestTaskOut]:
    """Queue the download + conversion of each product. Never waits for it."""
    return service.create(db, request)


@router.get("", response_model=list[IngestTaskOut])
def list_ingestions(
    location_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[IngestTaskOut]:
    return service.list(location_id=str(location_id) if location_id else None, limit=limit)


@router.get("/{task_id}", response_model=IngestTaskOut)
def get_ingestion(task_id: str) -> IngestTaskOut:
    return service.get(task_id)
