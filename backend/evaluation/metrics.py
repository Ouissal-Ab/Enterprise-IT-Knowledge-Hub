import json
import os

from app.database.session import SessionLocal
from app.services.rag_service import to_french, expand_query
from app.services.search_service import hybrid_search

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "questions.json"), encoding="utf-8") as f:
    questions = json.load(f)

K = 10


def rank_of(passages, source, page):
    # Rang (1 = premier) du bon passage dans les résultats, ou None.
    for i, p in enumerate(passages, start=1):
        if p["document"].startswith(source) and p["page"] == page:
            return i
    return None


def evaluate(db, use_expansion: bool):
    hits, reciprocal_sum, n = 0, 0.0, 0
    for q in questions:
        if q.get("source_attendue") is None:  # questions de refus : pas de source à retrouver
            continue
        n += 1
        french = to_french(q["question"])
        query = expand_query(french) if use_expansion else french
        passages = hybrid_search(db, query, top_k=K)
        rank = rank_of(passages, q["source_attendue"], q["page_attendue"])
        if rank:
            hits += 1
            reciprocal_sum += 1 / rank
    return hits / n, reciprocal_sum / n, n


if __name__ == "__main__":
    db = SessionLocal()
    try:
        for label, flag in [("Sans reformulation", False), ("Avec reformulation", True)]:
            hr, mrr, n = evaluate(db, flag)
            print(f"{label} : HR@{K} = {hr:.2f} | MRR@{K} = {mrr:.2f} | {n} questions")
    finally:
        db.close()