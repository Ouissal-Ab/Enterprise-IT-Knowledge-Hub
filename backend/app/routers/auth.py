from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.core.security import create_access_token, verify_password
from app.database.session import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == form_data.username.lower()).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    token = create_access_token(user.id, user.role)
    return {"access_token": token, "token_type": "bearer", "role": user.role}


@router.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
    }


@router.get("/admin-test")
def admin_only(admin: User = Depends(require_admin)):
    return {"message": f"Bienvenue {admin.first_name}"}