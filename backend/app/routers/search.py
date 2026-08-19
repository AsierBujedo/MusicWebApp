"""Search endpoint: GET /api/search?q="""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.track import SearchResults
from app.services import search_service

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResults)
async def search(
    q: str = Query(default="", max_length=200),
    _user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    return await search_service.search(db, q)
