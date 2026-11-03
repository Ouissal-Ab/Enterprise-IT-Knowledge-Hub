from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database.session import get_db
from app.models.category import Category
from app.models.document import Document
from app.models.user import User
from app.services.chunking_service import build_chunks, save_chunks
from app.services.document_service import (
    compute_hash,
    delete_stored_file,
    read_upload,
    store_file,
)
from app.services.extraction_service import extract_pages
from app.services.processing_service import process_document

router = APIRouter(prefix="/documents", tags=["Documents"])


def document_to_dict(document: Document) -> dict:
    return {
        "id": document.id,
        "title": document.title,
        "filename": document.filename,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "status": document.status,
        "category_id": document.category_id,
        "created_at": document.created_at,
    }


@router.post("/upload", status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    title: str = Form(..., min_length=3, max_length=255),
    category_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Catégorie introuvable.")

    content, file_type = await read_upload(file)
    file_hash = compute_hash(content)

    existing = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ce fichier existe déjà dans la base de connaissances.",
        )

    file_path = store_file(content, file_type)

    document = Document(
        title=title,
        filename=file.filename,
        file_path=file_path,
        file_type=file_type,
        file_size=len(content),
        file_hash=file_hash,
        status="pending",
        category_id=category_id,
        uploaded_by=current_user.id,
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        delete_stored_file(file_path)
        raise HTTPException(status_code=500, detail="Erreur lors de l'enregistrement du document.")

    background_tasks.add_task(process_document, document.id)

    return document_to_dict(document)


@router.get("/{document_id}/text-preview")
def preview_text(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document introuvable.")

    pages = extract_pages(document.file_path, document.file_type)

    return {
        "id": document.id,
        "filename": document.filename,
        "nb_pages": len(pages),
        "total_chars": sum(len(text) for _, text in pages),
        "first_page_text": pages[0][1][:3000] if pages else None,
    }


@router.post("/{document_id}/chunk")
def chunk_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document introuvable.")

    pages = extract_pages(document.file_path, document.file_type)
    chunks = build_chunks(pages)
    count = save_chunks(db, document, chunks)

    return {
        "id": document.id,
        "filename": document.filename,
        "num_chunks": count,
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document introuvable.")

    file_path = document.file_path
    db.delete(document)
    db.commit()
    delete_stored_file(file_path)

    return {"message": f"Document {document_id} supprimé."}