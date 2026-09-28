# Reconnaissance open source : ce qu'on reprend, ce qu'on écarte

(Anciennement `RECONNAISSANCE.md`.)

Date : 2026-09-28. Méthode : clone superficiel de chaque dépôt et lecture du **code, des exemples et des tests** (pas seulement des README). Aucune dépendance ajoutée « parce que c'est populaire ». Règle : on reprend une idée seulement si elle améliore une chose **mesurable ou démontrable** dans l'architecture existante.

Adoption : les étoiles GitHub n'ont pas été relevées (la recherche GitHub globale sort du périmètre autorisé de cette session) ;
l'activité est attestée par la date du dernier commit lu. Licences lues dans le fichier LICENSE du dépôt.

| Projet (commit lu) | Rôle | Composant pertinent lu | Licence | Activité | Utile pour nous ? | Ce qu'on reprend | Ce qu'on ne copie PAS | Décision |
|---|---|---|---|---|---|---|---|---|
| langchain-ai/langgraph `07b3318` | Graphes d'agents avec état | `types.py` : `interrupt`, `Command(resume=)` | MIT | 2026-09-27 | Patron oui, framework non | « Interrompre AVANT l'effet de bord, reprendre ensuite » | Le graphe piloté par LLM (notre flux est une machine d'états déterministe) | Patron adopté |
| langchain-ai/langchain `213f230` | Composants LLM | `agents/middleware/human_in_the_loop.py` (approve / edit / reject) | MIT | 2026-09-28 | Oui | Décisions « approuver / modifier / refuser » | Middleware complet | Adopté (MCP : message modifiable) |
| openai/openai-agents-python `08e5c43` | SDK d'agents | `guardrail.py` (garde-fous d'entrée/sortie à « tripwire ») | MIT | 2026-09-27 | Patron oui | Garde-fou qui bloque avant l'action | Dépendance au SDK / aux modèles OpenAI | Patron adopté (contenu membre non fiable, cf. SECURITE) |
| pydantic/pydantic-ai `ef13bc1` | Agents typés | `exceptions.ModelRetry`, `ApprovalRequiredToolset` | MIT | 2026-09-28 | Patron oui | Renvoyer l'erreur de validation au modèle pour UNE nouvelle tentative | Le framework d'agent | Adopté (réessai de validation du LLM) |
| crewAIInc/crewAI `4ed2abc` | Équipes d'agents par rôles | orchestration par rôles | MIT | 2026-09-25 | Non | — | Multi-agents pour un problème qui n'en a pas besoin | Écarté |
| microsoft/agent-framework `1370903` | Orchestration d'agents (successeur d'AutoGen) | samples `human-in-the-loop`, `tool-approval`, `checkpoint`, `evaluation` | MIT | 2026-09-28 | Patron oui | Évaluation par composant ; approbation d'outil | Workflows et hébergement Azure | Patrons confirmés |
| microsoft/autogen `027ecf0` | Multi-agents | README : **mode maintenance**, renvoie à agent-framework | CC-BY-4.0 (docs) / MIT (code) | 2026-04-06 | Non | — | — | Écarté (maintenance) |
| All-Hands-AI/OpenHands `c3c252a` | Agent de développement autonome | mode confirmation des actions risquées | MIT | 2026-09-28 | Patron | Confirmation humaine proportionnée au risque | Bac à sable d'exécution de code | Patron confirmé (annotations MCP lecture/écriture) |
| modelcontextprotocol/servers `f46d957` | Serveurs MCP de référence | structure des outils, validation d'entrée | transition de licence en cours (voir dépôt) | 2026-09-22 | Oui (référence) | Outils peu nombreux, annotés, erreurs lisibles | Accès fichiers/système | Référence suivie |
| PrefectHQ/fastmcp `89b00b7` | Framework MCP | `docs/servers/authorization.mdx`, fournisseurs d'auth, tests en mémoire | Apache-2.0 | 2026-09-27 | Oui | Jeton → identité + portées ; tests client en mémoire | La dépendance (le SDK officiel suffit) | Adopté (patrons) |
| a2aproject/a2a-python `0d5473c` | Protocole agent-à-agent | serveur de tâches, carte d'agent | Apache-2.0 | 2026-09-24 | Pas maintenant | — | Publier une « carte d'agent » sans implémenter le protocole serait trompeur | Différé : MCP couvre le besoin |
| qdrant/fastembed `9bf33d5` | Embeddings ONNX locaux | modèles denses, `sparse/bm25.py`, `rerank/cross_encoder` | Apache-2.0 | 2026-09-28 | Oui (déjà) | Miroir GCS du modèle e5 ; format ONNX | Les rerankers : tous sur Hugging Face (bloqué) | Déjà adopté (modèle) |
| FlagOpen/FlagEmbedding `fd1a2bd` | BGE-M3, rerankers | `research/BGE_M3` : score hybride pondéré | MIT | 2026-08-24 | Oui | Somme pondérée dense + lexical | Poids du modèle (réseau bloqué) | Idée adoptée, mesurée |
| UKPLab/sentence-transformers `4a3b5cd` | Embeddings / cross-encoders | `CrossEncoder` | Apache-2.0 | 2026-09-21 | Oui si modèle disponible | — | PyTorch (≈ 2 Go de dépendances) pour un seul reranker | Bloqué (modèles sur HF) |
| deepset-ai/haystack `c2e809e` | Pipelines de recherche | `_reciprocal_rank_fusion` (k = 61), évaluateurs | Apache-2.0 | 2026-09-28 | Partiellement | Métriques MRR / rappel | RRF : **mesurée et moins bonne ici** | RRF écartée, métriques adoptées |
| qdrant/qdrant `6ab21ca` | Base vectorielle | `full_scan_threshold` (10 000 Ko), filtres de charge utile | Apache-2.0 | 2026-09-03 | Non à notre échelle | Principe « filtrer puis classer » | Un service de plus à opérer | Écarté |
| pgvector/pgvector `7db2345` | Vecteurs dans Postgres | README : filtrage après l'index HNSW, « iterative scans » | PostgreSQL | 2026-09-22 | Non à notre échelle | Argument : filtrage *après* index peut perdre des résultats | — | Écarté |
| google/or-tools `100f66e` | Optimisation | `wedding_optimal_chart_sat.py`, `*_scheduling_sat.py` | Apache-2.0 | 2026-09-17 | Plus tard | Contraintes métier explicites | +dépendance pour un gain non nécessaire en 1:1 | Différé (tables de 3-4) |
| coleam00/ottomator-agents `2be20d5` | Exemples d'agents | pydantic-ai + MCP + RAG | MIT | 2025-11-09 | Non | — | — | Écarté |
| microsoft/spec-to-agents `f40268f` | Planification d'événements multi-agents | outil calendrier du « logistics manager » | MIT | 2026-04-22 | Partiellement | Export agenda | 5 agents LLM pour planifier | Adopté (.ics) |

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
