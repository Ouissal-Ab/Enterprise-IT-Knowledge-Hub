import re

import ollama
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.search_service import hybrid_search

_client = ollama.Client(host=settings.OLLAMA_BASE_URL)

REFUSAL = "Je ne connais pas cette information dans la base de connaissances."

FRENCH_WORDS = {
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "est", "je", "tu",
    "il", "elle", "nous", "vous", "mon", "ma", "mes", "pour", "dans", "sur",
    "comment", "quoi", "pourquoi", "où", "au", "aux", "que", "qui",
}

STRONG_MATCH_PHRASES = 3
CONTEXT_PASSAGES = 5

SYSTEM_PROMPT = """Tu es l'assistant de la base de connaissances IT d'Entreprise A.
Réponds en français, uniquement à partir des extraits fournis.
N'ajoute aucune information absente des extraits : pas de chiffre, de port, de paramètre ou de règle qui n'y figure pas mot pour mot.
Ne cite pas les extraits et n'écris aucun numéro d'extrait.
Si la réponse ne figure pas dans les extraits, réponds exactement : "Je ne connais pas cette information dans la base de connaissances." """

TRANSLATE_PROMPT = """Traduis la question suivante en français.
Réponds uniquement par la traduction, sans guillemets ni commentaire."""

SYNONYMS_PROMPT = """Tu aides une recherche dans une base de procédures IT.
Question : {question}
Donne 5 mots-clés ou synonymes français qui pourraient apparaître dans la réponse
(par exemple : durée, validité, expiration, délai, nombre, tentatives, verrouillage).
Réponds uniquement par les mots, séparés par des espaces, sans phrase."""


def is_french(text: str) -> bool:
    words = set(re.findall(r"[a-zàâçéèêëîïôûùüÿœ]+", text.lower()))
    return len(words & FRENCH_WORDS) > 0


def to_french(question: str) -> str:
    if is_french(question):
        return question

    response = _client.chat(
        model="qwen2.5:3b",
        messages=[
            {"role": "system", "content": TRANSLATE_PROMPT},
            {"role": "user", "content": question},
        ],
        options={"temperature": 0},
    )
    return response["message"]["content"].strip()


def expand_query(french_question: str) -> str:
    """Ajoute des synonymes à la question pour la recherche uniquement.
    En cas d'erreur, renvoie la question d'origine."""
    try:
        response = _client.chat(
            model="qwen2.5:3b",
            messages=[{"role": "user", "content": SYNONYMS_PROMPT.format(question=french_question)}],
            options={"temperature": 0},
        )
        extra = re.sub(r"[^\w\s-]", " ", response["message"]["content"]).strip()
        return f"{french_question} {extra}"[:300]
    except Exception:
        return french_question


def build_context(passages: list[dict]) -> str:
    return "\n\n".join(
        f"Extrait {i}\n{p['content']}" for i, p in enumerate(passages, start=1)
    )


def _phrases(text: str, size: int = 4) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-zàâçéèêëîïôûùüÿœ0-9]+", text.lower())
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def _words(text: str, min_len: int = 4) -> set[str]:
    return {
        w for w in re.findall(r"[a-zàâçéèêëîïôûùüÿœ0-9]+", text.lower())
        if len(w) >= min_len
    }


def best_passage(answer: str, passages: list[dict]) -> dict | None:
    # 1. Cas général : le passage partage assez de suites de 4 mots avec la réponse.
    answer_phrases = _phrases(answer)
    scored = [
        (len(answer_phrases & _phrases(p["content"])), -i, p)
        for i, p in enumerate(passages)
    ]
    score, _, best = max(scored, key=lambda t: (t[0], t[1]))
    if score >= STRONG_MATCH_PHRASES:
        return best

    # 2. Réponse courte (ex. « 180 jours ») : tous les chiffres de la réponse
    #    doivent figurer dans un des 3 meilleurs passages, avec au moins 4 mots communs.
    numbers = set(re.findall(r"\d+", answer))
    if not numbers:
        return None
    answer_words = _words(answer)
    for p in passages[:3]:
        content_numbers = set(re.findall(r"\d+", p["content"]))
        if numbers <= content_numbers and len(answer_words & _words(p["content"])) >= 4:
            return p
    return None


def clean_answer(raw: str) -> str:
    return re.sub(r"\s*SOURCES\s*:.*$", "", raw, flags=re.DOTALL | re.IGNORECASE).strip()


def ask_qwen(question: str, passages: list[dict]) -> str:
    user_message = (
        f"Extraits :\n\n{build_context(passages)}\n\n"
        f"Question : {question}\n\n"
        "Réponds à la question à partir des extraits."
    )
    response = _client.chat(
        model="qwen2.5:3b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        options={"temperature": 0},
    )
    return clean_answer(response["message"]["content"])


def is_refusal(answer: str) -> bool:
    return "Je ne connais pas cette information" in answer


def refusal(question: str, french_question: str) -> dict:
    return {
        "question": question,
        "question_recherchee": french_question,
        "answer": REFUSAL,
        "sources": [],
    }


def answer_question(db: Session, question: str) -> dict:
    french_question = to_french(question)

    # La recherche utilise la question enrichie de synonymes ;
    # la réponse de Qwen reste basée sur la question d'origine.
    search_query = expand_query(french_question)
    passages = hybrid_search(db, search_query, top_k=CONTEXT_PASSAGES)

    if not passages:
        return refusal(question, french_question)

    answer = ask_qwen(french_question, passages)

    if is_refusal(answer):
        return refusal(question, french_question)

    # Vérification : la réponse doit être étayée par un passage, sinon refus.
    source = best_passage(answer, passages)
    if source is None:
        return refusal(question, french_question)

    return {
        "question": question,
        "question_recherchee": french_question,
        "answer": answer,
        "sources": [
            {"document": source["document"], "page": source["page"]}
        ],
    }