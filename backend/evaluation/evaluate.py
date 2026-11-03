import json
import os
import sys

import httpx

BASE_URL = "http://localhost:8000"
HERE = os.path.dirname(os.path.abspath(__file__))
REFUSAL_TEXT = "Je ne connais pas cette information"


def main():
    if len(sys.argv) < 2:
        print("Usage : python evaluation/evaluate.py TOKEN")
        return

    token = sys.argv[1]
    with open(os.path.join(HERE, "questions.json"), encoding="utf-8") as f:
        questions = json.load(f)

    headers = {"Authorization": f"Bearer {token}"}
    auto_points = 0
    auto_max = 0

    for i, q in enumerate(questions, start=1):
        print(f"\n{i}. {q['question']}")
        try:
            response = httpx.get(
                f"{BASE_URL}/chat",
                params={"q": q["question"]},
                headers=headers,
                timeout=600,
            )
        except Exception as error:
            print(f"   ERREUR DE CONNEXION : {error}")
            auto_max += 2 if q["reponse_attendue"] == "REFUS" else 1
            continue

        print(f"   Code HTTP : {response.status_code}")

        try:
            data = response.json()
        except ValueError:
            print(f"   Réponse non JSON : {response.text[:300]}")
            auto_max += 2 if q["reponse_attendue"] == "REFUS" else 1
            continue

        if "answer" not in data:
            print(f"   Réponse sans champ answer : {str(data)[:300]}")
            auto_max += 2 if q["reponse_attendue"] == "REFUS" else 1
            continue

        answer = data.get("answer", "")
        sources = data.get("sources", [])
        refused = REFUSAL_TEXT in answer

        if q["reponse_attendue"] == "REFUS":
            ok = refused and not sources
            auto_max += 2
            auto_points += 2 if ok else 0
            print(f"   Refus correct : {'OUI' if ok else 'NON'}")
            print(f"   Réponse : {answer[:200]}")
        else:
            source_ok = any(
                s["document"] == q["source_attendue"] and s["page"] == q["page_attendue"]
                for s in sources
            )
            auto_max += 1
            auto_points += 1 if source_ok else 0
            found = [(s["document"], s["page"]) for s in sources]
            print(f"   Source correcte : {'OUI' if source_ok else 'NON'} {found}")
            print(f"   Réponse à vérifier : {answer}")

    print(f"\nScore automatique : {auto_points} / {auto_max}")
    print("À compléter à la main : pour chaque réponse non-refus, 1 point si elle est juste, 1 point si rien n'est inventé.")


if __name__ == "__main__":
    main()