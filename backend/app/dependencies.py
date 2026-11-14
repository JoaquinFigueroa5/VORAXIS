from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session

DbSession = Annotated[Session, Depends(get_session)]

Limit = Annotated[int, Query(ge=1, le=200, description="Page size")]
Offset = Annotated[int, Query(ge=0, description="Rows to skip")]
