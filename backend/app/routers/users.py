from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.security import hash_password
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["Gestion des utilisateurs"])


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at,
    }


@router.get("")
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.last_name, User.first_name).all()
    return [user_to_dict(u) for u in users]


@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    return user_to_dict(user)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    existing = db.query(User).filter(func.lower(User.email) == user_data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cet e-mail est déjà utilisé.")

    new_user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "Compte créé avec succès",
        "id": new_user.id,
        "email": new_user.email,
        "role": new_user.role,
    }


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    data = payload.model_dump(exclude_unset=True, exclude_none=True)

    if "email" in data:
        exists = (
            db.query(User)
            .filter(func.lower(User.email) == data["email"], User.id != user_id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="Cet e-mail est déjà utilisé.")

    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user_to_dict(user)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas supprimer votre propre compte.",
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    db.delete(user)
    db.commit()
    return {"message": f"Utilisateur {user_id} supprimé."}