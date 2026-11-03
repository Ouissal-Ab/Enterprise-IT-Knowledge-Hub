import ollama
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import SessionLocal
from app.models.chunk import Chunk
from app.models.document import Document
from app.services.chunking_service import build_chunks, save_chunks
from app.services.extraction_service import extract_pages

_ollama_client = ollama.Client(host=settings.OLLAMA_BASE_URL)


def embed_text(text: str) -> list[float]:
    response = _ollama_client.embeddings(model="nomic-embed-text", prompt=text)
    return response["embedding"]


def process_document(document_id: int) -> None:
    """Traite un document en arrière-plan : extraction, découpage, embeddings, statut."""
    db: Session = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return

        document.status = "processing"
        document.error_message = None
        db.commit()

        pages = extract_pages(document.file_path, document.file_type)
        chunks = build_chunks(pages)
        if not chunks:
            raise ValueError("Aucun texte exploitable n'a été extrait du document.")

        save_chunks(db, document, chunks)

        pending_chunks = (
            db.query(Chunk)
            .filter(Chunk.document_id == document.id, Chunk.embedding.is_(None))
            .order_by(Chunk.position)
            .all()
        )
        for chunk in pending_chunks:
            chunk.embedding = embed_text(chunk.content)
        db.commit()

        document.status = "indexed"
        db.commit()

    except Exception as exc:
        db.rollback()
        document = db.get(Document, document_id)
        if document is not None:
            document.status = "failed"
            document.error_message = str(exc)[:1000]
            db.commit()
    finally:
        db.close()