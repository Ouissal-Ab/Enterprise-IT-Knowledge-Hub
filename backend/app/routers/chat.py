from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.rag_service import answer_question

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("")
def chat(
    q: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return answer_question(db, q)