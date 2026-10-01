> **HISTORIQUE — rédigé avant le registre des capacités (28–30.09.2026).** Conservé pour la traçabilité des décisions ; ne décrit PAS le produit actuel, et ses chiffres, routes et noms de fichiers peuvent être faux aujourd'hui. État actuel : [README](/README.md) · [index de la documentation](/docs/README.md).

# Architecture du prototype précédent « Le Fil du Club » (toujours servi : /, /demo/stage, /decision…)

> Club Pulse (/app, /console, `intelligence/`) est décrit dans [ARCHITECTURE.md](ARCHITECTURE.md). Ce document reste exact pour les modules historiques.

**Principe : l'IA peut suggérer ; le code déterministe valide ; l'humain décide.**
Chaque bloc ci-dessous existe dans le dépôt (chemins sous `prototype/`). Rien n'est décrit qui n'est pas implémenté.

```
            Membre (web /)          Assistant IA externe (Claude Desktop, Claude Code… via MCP)
                 │                                     │
                 │                     app/mcp_serveur.py : client MINCE de l'API
                 │                     (10 outils, jetons + portées en HTTP, confirmation humaine par elicitation)
                 ▼                                     ▼
        ┌───────────────────────── API FastAPI : app/main.py (autorité unique) ─────────────────────────┐
        │                                                                                               │
        │  1. COMPRENDRE le besoin                                                                      │
        │     parser_rules.py   règles + taxonomie (FR/DE/EN), négations, préférences, lieux, faux amis │
        │     analyse.py        si aucune compétence : semantique.py (e5 local, ONNX, CPU) PROPOSE 1-3  │
        │                       compétences → le membre CONFIRME (jamais de décision automatique)       │
        │     parser_llm.py     option : Claude ou Apertus (API compatible OpenAI), sortie JSON          │
        │                       contrainte, 1 réessai sur erreur de validation, repli visible sur règles│
        │     → valider() : vocabulaire fermé, extraits vérifiés dans le texte du demandeur             │
        │                                                                                               │
        │  2. TROUVER  matching.py                                                                      │
        │     filtres durs (code) : consentement, disponibilité, communauté, zone, implantation,        │
        │       langue, concurrence, exclusions  →  jamais contournables par un modèle                  │
        │     pertinence : offre déclarée > présentation affirmative > mots (hors catalogue) ;          │
        │     preuves citées MOT POUR MOT (preuve_valide) ; abstention si rien de fiable                │
        │     expliquer() : critère par critère ; raisons de consentement jamais divulguées             │
        │                                                                                               │
        │  3. METTRE EN RELATION  store.py (SQLite)                                                     │
        │     machine d'états + rôles : proposée → acceptée → rencontre planifiée → faite → clôturée    │
        │     revérification serveur (on ne sollicite que qui correspond), anonymat levé à l'acceptation,│
        │     versions de besoin, retrait du consentement en cascade ;
        │     agenda.py : créneaux communs (privés, seulement après acceptation) pour planifier                                    │
        │                                                                                               │
        │  4. OPTIMISER la soirée  soiree.py                                                            │
        │     valeur d'une rencontre = aides prouvées (même moteur) ; langue commune obligatoire ;      │
        │     programme linéaire en nombres entiers (scipy/HiGHS), optimum PROUVÉ ou signalé ;          │
        │     comparé au glouton et à l'aléatoire ; absences expliquées ; export .ics                   │
        │                                                                                               │
        │  5. PILOTER le Club  club.py : compétences à recruter, offres dormantes (agrégats, sans noms)│
        │                                                                                               │
        │  Sécurité transverse  securite.py : texte des membres = donnée non fiable ; le LLM d'analyse  │
        │     ne reçoit jamais les profils ; signaux d'instructions ; télémétrie onnxruntime coupée     │
        └───────────────────────────────────────────────────────────────────────────────────────────────┘
                 │
          HACKVS_MODE=demo (profils FICTIFS, identité choisie)  |  HACKVS_MODE=reel (fichier autorisé seulement ;
                                                                 sinon 503/501, jamais de simulation)
```

## Qui fait quoi (et pourquoi)

| Composant | Rôle | Pourquoi ce choix | Ce qu'il n'a PAS le droit de faire |
|---|---|---|---|
| Règles + taxonomie | Extraire les critères, négations, lieux | Précis, explicable, instantané (≈ 2 ms) | — |
| Embeddings locaux (multilingual-e5-large) | Proposer des compétences quand les règles échouent | Multilingue, hors ligne, sans clé | Décider seuls (mesuré : aucun seuil ne sépare « hors catalogue » de « vrai besoin ») |
| LLM (Claude / Apertus) | Comprendre des formulations riches | Nuance, paraphrases | Ajouter une compétence hors vocabulaire, voir les profils, rendre quelqu'un éligible |
| Filtres durs (code) | Consentement, zone, langue, concurrence | Garanties vérifiables | Être contournés |
| MILP (HiGHS) | Plan de soirée | Optimum prouvé en ≈ 70 ms pour 122 participants | Inventer une aide non prouvée |
| API | Autorité unique | Une seule implémentation des règles | — |
| MCP | Accès agent | Standard ouvert, aucun code métier dupliqué | Agir sans confirmation humaine ni hors de ses portées |

## Garanties testées (extraits de `tests/`)
- Aucun visiteur ni membre refusant les introductions n'apparaît, jamais (évaluation + tests).
- Toute preuve affichée se retrouve mot pour mot dans le profil.
- On ne peut solliciter qu'un membre que le moteur propose (vérifié côté serveur, y compris via MCP).
- Un besoin anonyme reste anonyme jusqu'à l'acceptation (web et MCP).
- Le LLM ne reçoit jamais le texte des profils ; un profil contenant des consignes ne change pas le classement.
- MCP : sans jeton → 401 ; portée « lecture » ne peut pas écrire ; refus du membre = rien envoyé.
- Plan de soirée : ≤ 1 rencontre par personne et par tour, pas de paire répétée, langue commune, optimum ≥ glouton.
- Mode réel : aucune simulation, aucun journal exposé.

## Choix d'infrastructure
- **Pas de base vectorielle** : 37 à 150 profils ; parcours exhaustif exact après filtrage (Qdrant fait lui-même un parcours exhaustif sous son seuil). Voir OPEN_SOURCE_RECON.md.
- **Pas de framework d'agents** : les parcours sont des machines d'états déterministes ; les patrons utiles (interruption avant effet de bord, approuver/modifier/refuser, réessai de validation) sont repris sans la dépendance.
- **CPU seulement** : modèle ONNX 2,2 Go ; suggestion mesurée à ≈ 77 ms en médiane (max 103 ms, 12 requêtes, 4 cœurs), après un chargement initial en arrière-plan ; le produit fonctionne sans lui.
