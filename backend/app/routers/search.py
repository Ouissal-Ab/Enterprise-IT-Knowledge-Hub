from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.search_service import semantic_search

router = APIRouter(prefix="/search", tags=["Recherche"])


@router.get("")
def search(
    q: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return {"question": q, "results": semantic_search(db, q)}