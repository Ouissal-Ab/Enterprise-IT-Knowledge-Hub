from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database.session import get_db
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Catégories"])


def category_to_dict(category: Category) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "num_documents": len(category.documents),
        "created_at": category.created_at,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    name = data.name.strip()
    existing = db.query(Category).filter(func.lower(Category.name) == name.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cette catégorie existe déjà.")

    category = Category(name=name, description=data.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category_to_dict(category)


@router.get("")
def list_categories(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    categories = db.query(Category).order_by(Category.name).all()
    return [category_to_dict(c) for c in categories]


@router.put("/{category_id}")
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Catégorie introuvable.")

    if data.name is not None:
        name = data.name.strip()
        existing = (
            db.query(Category)
            .filter(func.lower(Category.name) == name.lower(), Category.id != category_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Une autre catégorie porte déjà ce nom.")
        category.name = name

    if data.description is not None:
        category.description = data.description

    db.commit()
    db.refresh(category)
    return category_to_dict(category)


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Catégorie introuvable.")

    if category.documents:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de supprimer : {len(category.documents)} document(s) utilisent cette catégorie.",
        )

    db.delete(category)
    db.commit()
    return {"message": f"Catégorie « {category.name} » supprimée."}