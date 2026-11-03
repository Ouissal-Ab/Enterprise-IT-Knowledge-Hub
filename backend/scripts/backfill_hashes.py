import hashlib
from pathlib import Path

from app.database.session import SessionLocal
from app.models.document import Document

db = SessionLocal()
try:
    documents = db.query(Document).filter(Document.file_hash.is_(None)).all()
    for doc in documents:
        path = Path(doc.file_path)
        if path.exists():
            doc.file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    db.commit()
    print(f"{len(documents)} document(s) traité(s).")
finally:
    db.close()