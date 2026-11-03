# Enterprise IT Knowledge Hub

Assistant qui répond aux questions sur les procédures IT d'une entreprise, à partir de ses documents internes. Chaque réponse indique le document et la page source. Si l'information n'existe pas dans les documents, l'assistant le dit au lieu d'inventer.

Projet de démonstration. L'entreprise et les documents sont fictifs.

## Problème

Les procédures IT sont dispersées dans de nombreux documents. Les employés perdent du temps à les chercher, et le support répond souvent à des questions déjà documentées. Le projet permet de poser la question en langage naturel et d'obtenir une réponse avec sa source.

## Type de RAG

Le projet utilise un RAG (Retrieval-Augmented Generation) à recherche hybride :

- **Recherche sémantique** : les passages et la question sont transformés en vecteurs (embeddings `nomic-embed-text`), et on cherche les passages les plus proches, avec pgvector.
- **Recherche par mots-clés (BM25)** : PostgreSQL recherche les termes exacts, avec la configuration française.
- **Fusion** : les deux classements sont combinés avec la méthode RRF (Reciprocal Rank Fusion).
- **Génération** : un modèle local (qwen2.5:3b via Ollama) rédige la réponse uniquement à partir des passages retrouvés, puis une vérification contrôle que la réponse est bien étayée par un passage.

## Stack

- **Backend** : FastAPI, SQLAlchemy, PostgreSQL avec pgvector
- **Modèles** : Ollama (qwen2.5:3b, nomic-embed-text)
- **Frontend** : Next.js, TypeScript
- **Infrastructure** : Docker Compose

## Documentation de l'API

Une fois le backend lancé en local, la documentation de l'API est disponible sur `/docs` (Swagger).

## Évaluation

La qualité de la recherche est mesurée sur un jeu de questions de test avec deux indicateurs :

- **HR@10** (Hit Rate) : proportion de questions dont le bon document apparaît dans les 10 premiers résultats.
- **MRR@10** (Mean Reciprocal Rank) : position moyenne du bon document dans ces 10 résultats, plus il est haut, mieux c'est.

Les refus hors sujet sont également testés, pour vérifier que l'assistant ne répond pas à une question qui n'appartient pas à la base.