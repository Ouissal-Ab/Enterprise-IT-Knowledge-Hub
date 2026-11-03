import re

import ollama
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chunk import Chunk
from app.models.document import Document

_client = ollama.Client(host=settings.OLLAMA_BASE_URL)

MAX_DISTANCE = 0.38
RRF_K = 60

STOPWORDS = {
    "comment", "quoi", "pour", "dans", "depuis", "chez", "avec", "sans",
    "les", "des", "une", "est", "que", "qui", "quel", "quelle", "faire",
}


def embed_query(text: str) -> list[float]:
    response = _client.embeddings(model="nomic-embed-text", prompt=text)
    return response["embedding"]


def _format(rows) -> list[dict]:
    return [
        {
            "document": doc.filename,
            "title": doc.title,
            "page": chunk.page,
            "content": chunk.content,
            "distance": distance,
        }
        for chunk, doc, distance in rows
    ]


def semantic_search(db: Session, question: str, top_k: int = 5) -> list[dict]:
    query_vector = embed_query(question)
    distance = Chunk.embedding.cosine_distance(query_vector)

    rows = (
        db.query(Chunk, Document, distance.label("distance"))
        .join(Document, Chunk.document_id == Document.id)
        .filter(Chunk.embedding.is_not(None))
        .filter(distance <= MAX_DISTANCE)
        .order_by(distance)
        .limit(top_k)
        .all()
    )
    return [
        {**item, "distance": round(float(item["distance"]), 4)}
        for item in _format(rows)
    ]


def _semantic_ids(db: Session, question: str, limit: int) -> dict[int, float]:
    query_vector = embed_query(question)
    distance = Chunk.embedding.cosine_distance(query_vector)
    rows = (
        db.query(Chunk.id, distance.label("distance"))
        .filter(Chunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
        .all()
    )
    return {row.id: float(row.distance) for row in rows}


def _keyword_ids(db: Session, question: str, limit: int) -> list[int]:
    terms = [
        t for t in re.findall(r"[a-zàâçéèêëîïôûùüÿœ0-9]+", question.lower())
        if len(t) > 2 and t not in STOPWORDS
    ]
    if not terms:
        return []

    ts_query = func.to_tsquery("french", " | ".join(terms))
    ts_vector = func.to_tsvector("french", Chunk.content)
    rank = func.ts_rank(ts_vector, ts_query).label("rank")

    rows = (
        db.query(Chunk.id, rank)
        .filter(ts_vector.op("@@")(ts_query))
        .order_by(rank.desc())
        .limit(limit)
        .all()
    )
    return [row.id for row in rows]


def _rrf(ranked_lists: list[list[int]]) -> list[int]:
    scores: dict[int, float] = {}
    for ids in ranked_lists:
        for position, chunk_id in enumerate(ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (RRF_K + position)
    return sorted(scores, key=scores.get, reverse=True)


def hybrid_search(db: Session, question: str, top_k: int = 5) -> list[dict]:
    semantic = _semantic_ids(db, question, limit=20)
    relevant_semantic = [cid for cid, dist in semantic.items() if dist <= MAX_DISTANCE]
    keyword = _keyword_ids(db, question, limit=20)

    if not relevant_semantic and not keyword:
        return []

    fused = _rrf([relevant_semantic, keyword])[:top_k]
    if not fused:
        return []

    rows = (
        db.query(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .filter(Chunk.id.in_(fused))
        .all()
    )
    by_id = {chunk.id: (chunk, doc) for chunk, doc in rows}

    results = []
    for cid in fused:
        chunk, doc = by_id[cid]
        results.append({
            "document": doc.filename,
            "title": doc.title,
            "page": chunk.page,
            "content": chunk.content,
            "distance": round(semantic[cid], 4) if cid in semantic else None,
        })
    return results