# Reconnaissance open source : ce qu'on reprend, ce qu'on écarte

Date : 2026-09-28. Méthode : clone superficiel de chaque dépôt et lecture du **code, des exemples et des tests** (pas seulement des README). Aucune dépendance ajoutée « parce que c'est populaire ». Règle : on reprend une idée seulement si elle améliore une chose **mesurable ou démontrable** dans l'architecture existante.

| Dépôt | Commit lu | Fichiers lus en priorité |
|---|---|---|
| langchain-ai/langgraph | `07b3318` (2026-09-27) | `libs/langgraph/langgraph/types.py` (`interrupt`, `Command`) |
| PrefectHQ/fastmcp | `89b00b7` (2026-09-27) | `docs/servers/authorization.mdx`, `auth/providers/*`, `docs/servers/testing.mdx` |
| deepset-ai/haystack | `c2e809e` (2026-09-28) | `utils/misc.py::_reciprocal_rank_fusion`, `components/evaluators/*`, `rankers/llm_ranker.py` |
| FlagOpen/FlagEmbedding | `fd1a2bd` (2026-08-24) | `research/BGE_M3/README.md` (score hybride dense+sparse+multi-vecteur), `examples/inference/*` |
| qdrant/qdrant | `6ab21ca` (2026-09-03) | `lib/segment/src/index/*`, OpenAPI (`full_scan_threshold`) |
| google/or-tools | `100f66e` (2026-09-17) | `examples/python/wedding_optimal_chart_sat.py`, `*_scheduling_sat.py` |
| microsoft/agent-framework | `1370903` (2026-09-28) | `python/samples/03-workflows/{human-in-the-loop,tool-approval,checkpoint,evaluation}` |
| coleam00/ottomator-agents | `2be20d5` (2025-11-09) | inventaire des agents (pydantic-ai + MCP, RAG) |
| langchain-ai/langchain | `213f230` (2026-09-28) | `agents/middleware/human_in_the_loop.py` |
| pgvector/pgvector | `7db2345` (2026-09-22) | README : filtrage *après* l'index HNSW, « iterative index scans », recherche hybride |
| microsoft/spec-to-agents | `f40268f` (2026-04-22) | `src/spec_to_agents/{agents,tools,workflow}` (planification d'événements multi-agents) |

## Constat de départ (mesuré avant la reconnaissance)

Sur les exemples de besoin « énergie », l'IA locale (prototypes e5 seuls) proposait :
« Je cherche un expert en énergie » → *efficacité énergétique, export Suisse alémanique, fiduciaire* (solaire absent, 2 options sur 3 hors sujet) ;
« …dans les renouvelables » → *recrutement* en premier. Le signal dense seul est trop « plat » (tous les scores entre 0,84 et 0,88).
C'est la faiblesse qui a orienté le classement ci-dessous.

## Carte des opportunités (classée par valeur / coût)

| # | Idée (source) | Améliore | Coût | Risque | Bénéfice visible pour le jury | Décision |
|---|---|---|---|---|---|---|
| 1 | **Fusion hybride dense + lexical** : RRF à k = 61 (Haystack `DocumentJoiner`) ; score hybride dense + sparse de BGE-M3 | recherche sémantique, multilingue | faible (≈ 100 lignes, zéro dépendance) | faible (mesuré sur dev + réservé) | Les 3 compétences proposées deviennent plausibles ; « je ne sais pas » quand rien ne ressort | **Adopté** |
| 2 | **Approuver / modifier / refuser** avant toute action (LangChain `HumanInTheLoopMiddleware`, LangGraph `interrupt`, Agent Framework `tool-approval`) | humain dans la boucle, MCP | faible | faible (l'API revérifie tout) | Le membre peut corriger le message que l'assistant allait envoyer | **Adopté** |
| 3 | **MCP distant authentifié** : jeton → membre + portées lecture/écriture (FastMCP `require_scopes`, vérificateur de jetons du SDK officiel) | MCP, déploiement, mode réel | moyen | moyen (sécurité : testé) | L'assistant d'un membre ne peut agir qu'en son nom, et l'écriture exige une portée | **Adopté** |
| 4 | **Export calendrier** du programme de soirée (outil calendrier du *Logistics Manager* de spec-to-agents) | UX/démo, planification | faible (RFC 5545, stdlib) | faible | « Ajouter à mon agenda » depuis le plan de soirée | **Adopté** |
| 5 | **Contraintes réalistes du plan** : langue commune obligatoire, explication des personnes non placées (modèle *wedding seating* d'OR-Tools : contraintes métier explicites) | optimisation | faible (reste en MILP HiGHS) | faible | Plus de rencontre entre deux personnes sans langue commune ; chaque absence expliquée | **Adopté** |
| 6 | Métriques de recherche standard (MRR, rappel@3 : évaluateurs Haystack ; évaluation par composant : Agent Framework `evaluate_workflow`) | évaluation | très faible | nul | Chiffres comparables à la littérature | **Adopté** (dans #1) |
| 7 | Reranker *cross-encoder* multilingue (BGE-reranker-v2-m3) | reranking | moyen | — | Potentiellement fort | **Bloqué** : poids uniquement sur Hugging Face / ModelScope, refusés par la politique réseau (vérifié). Miroir GCS de fastembed : pas de reranker multilingue |
| 8 | Tables de 3-4 personnes (CP-SAT, modèle *wedding chart* d'OR-Tools) | optimisation | moyen (+ dépendance ortools) | moyen | Tables thématiques | **Différé** : les rencontres 1:1 correspondent au besoin « mise en relation » ; HiGHS prouve déjà l'optimum |
| 9 | Base vectorielle (Qdrant, pgvector) | recherche | moyen | moyen | Faible | **Écarté** : à l'échelle d'un Club (≤ 10⁴ profils), Qdrant lui-même fait un parcours exhaustif sous `full_scan_threshold` ; pgvector documente que le filtrage *après* l'index HNSW peut perdre des résultats. Notre ordre « filtres durs d'abord, puis classement exact » garantit zéro violation |
| 10 | Orchestration par graphe d'agents (LangGraph, Agent Framework, spec-to-agents multi-agents) | agents | élevé | élevé | Faible | **Écarté comme framework, repris comme patrons** : nos parcours sont des machines d'états déterministes (SQLite) ; l'« interrupt avant effet de bord » est déjà notre règle (résolveur MCP exécuté avant le corps de l'outil). Confier le flux de contrôle à un LLM contredirait « l'IA suggère, les règles décident » |
| 11 | Agents pratiques (oTTomator : pydantic-ai + MCP + RAG) | agents | — | — | — | **Rien de spécifique à reprendre** : confirme le choix « un serveur MCP, n'importe quel agent » |
| 12 | Assistant conversationnel dans le produit (appel d'outils LLM sur les mêmes outils que le MCP) | agents, démo | moyen | moyen | Fort | **Bloqué par la clé** (Claude ou Apertus) : prévu derrière le fournisseur interchangeable existant |

## Réponse à « que pourrait construire une autre excellente équipe que nous ne pouvons pas ? »

1. Un **reranker neuronal multilingue** (bloqué par le réseau, pas par nous) : on obtient l'essentiel de l'effet par la fusion hybride, mesurée.
2. Un **assistant conversationnel** branché sur un LLM : notre serveur MCP rend cela possible *sans rien réécrire* ; il manque uniquement une clé autorisée.
3. Un **accès agent sécurisé et distant** : c'est ce qu'on construit (#2, #3), là où la plupart des équipes exposent un chatbot sans garde-fous.

Les résultats mesurés de chaque idée adoptée sont dans [EVALUATION.md](EVALUATION.md).
