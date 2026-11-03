import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_TYPES = {"pdf", "html", "md"}
CHUNK_SIZE = 1024 * 1024


def get_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext == "htm":
        ext = "html"
    if ext == "markdown":
        ext = "md"
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non accepté : .{ext}. Formats acceptés : pdf, html, md.",
        )
    return ext


def check_content(content: bytes, file_type: str) -> None:
    if file_type == "pdf":
        if not content.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Le fichier n'est pas un vrai PDF.")
    else:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Le fichier n'est pas un texte UTF-8 valide.")


async def read_upload(file: UploadFile) -> tuple[bytes, str]:
    file_type = get_file_type(file.filename or "")
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    content = bytearray()
    while chunk := await file.read(CHUNK_SIZE):
        content.extend(chunk)
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Fichier trop volumineux (limite : {settings.MAX_UPLOAD_SIZE_MB} Mo).",
            )

    check_content(bytes(content), file_type)
    return bytes(content), file_type


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def store_file(content: bytes, file_type: str) -> str:
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{file_type}"
    file_path = upload_dir / stored_name
    file_path.write_bytes(content)
    return str(file_path)


def delete_stored_file(file_path: str) -> None:
    Path(file_path).unlink(missing_ok=True)