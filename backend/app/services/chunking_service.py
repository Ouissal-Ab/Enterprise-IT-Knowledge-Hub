import re

from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.document import Document

MAX_WORDS = 500

# Lignes de mise en page, présentes sur chaque page et sans intérêt pour la recherche.
NOISE_PATTERNS = [
    re.compile(r"^ENTREPRISE A — Direction des Systèmes d'Information$"),
    re.compile(r"^[A-Z]{2,}-[A-Z0-9-]+ · v[\d.]+$"),
    re.compile(r"^Classification : Interne"),
    re.compile(r"^Page \d+ / \d+$"),
]


def _clean_text(text: str) -> str:
    lines = [
        line for line in text.split("\n")
        if not any(pattern.match(line.strip()) for pattern in NOISE_PATTERNS)
    ]
    return "\n".join(lines)


def _split_units(text: str) -> list[tuple[str, bool]]:
    """Regroupe les lignes en blocs : paragraphes (False) ou tableaux (True)."""
    units: list[tuple[str, bool]] = []
    current: list[str] = []
    current_is_table = False

    for line in text.split("\n"):
        if not line.strip():
            continue
        is_table = " | " in line
        if current and is_table != current_is_table:
            units.append(("\n".join(current), current_is_table))
            current = []
        current_is_table = is_table
        current.append(line)

    if current:
        units.append(("\n".join(current), current_is_table))
    return units


def _flush(chunks: list[dict], page_number: int, buffer: list[str]) -> None:
    if buffer:
        chunks.append({"page": page_number, "content": "\n\n".join(buffer)})
        buffer.clear()


def build_chunks(pages: list[tuple[int, str]]) -> list[dict]:
    """
    Découpe le texte de chaque page :
    - les tableaux restent entiers ;
    - les petits paragraphes sont regroupés jusqu'à MAX_WORDS mots ;
    - les très longs paragraphes sont coupés tous les MAX_WORDS mots.
    """
    chunks: list[dict] = []

    for page_number, text in pages:
        buffer: list[str] = []
        buffer_words = 0

        for block, is_table in _split_units(_clean_text(text)):
            words = len(block.split())

            if is_table:
                _flush(chunks, page_number, buffer)
                buffer_words = 0
                chunks.append({"page": page_number, "content": block})
                continue

            if words > MAX_WORDS:
                _flush(chunks, page_number, buffer)
                buffer_words = 0
                block_words = block.split()
                for start in range(0, len(block_words), MAX_WORDS):
                    piece = " ".join(block_words[start:start + MAX_WORDS])
                    chunks.append({"page": page_number, "content": piece})
                continue

            if buffer_words + words > MAX_WORDS:
                _flush(chunks, page_number, buffer)
                buffer_words = 0

            buffer.append(block)
            buffer_words += words

        _flush(chunks, page_number, buffer)

    return chunks


def save_chunks(db: Session, document: Document, chunks: list[dict]) -> int:
    """Remplace les anciens morceaux du document par les nouveaux."""
    db.query(Chunk).filter(Chunk.document_id == document.id).delete()

    for position, item in enumerate(chunks, start=1):
        db.add(
            Chunk(
                document_id=document.id,
                position=position,
                page=item["page"],
                content=item["content"],
            )
        )

    document.num_chunks = len(chunks)
    db.commit()
    return len(chunks)