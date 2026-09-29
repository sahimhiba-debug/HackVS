# ADR 0001 — Adaptateur Apertus : client HTTP compatible OpenAI, sans SDK

Statut : **accepté** (prototype). Date : 2026-09-29.

## Contexte
Le Club veut une IA suisse et ouverte. Apertus (EPFL, ETH Zurich, CSCS) est servi par des hébergeurs via une API
compatible OpenAI. Aucun identifiant n'est disponible dans notre environnement.

## Décision
`intelligence/ia.py::Apertus` parle HTTP (`httpx`) au point `/chat/completions` de `APERTUS_BASE_URL`, avec
`temperature=0`, sortie JSON contrainte quand le schéma est fourni (repliée sur la seule consigne si le serveur refuse `response_format`), délai `APERTUS_DELAI_S` (30 s par défaut). Aucun SDK tiers. Toute panne est
traduite en `ErreurFournisseur(cause, reessayable)` : c'est le SEUL type qu'un fournisseur lève.

## Alternatives écartées
- SDK OpenAI : dépendance lourde pour un seul point d'accès, et laisse croire à un fournisseur OpenAI.
- Modèle local (ONNX, déjà utilisé pour la sémantique) pour la génération : trop lourd pour la démonstration.

## Conséquences
+ Un hébergeur ou un autre modèle compatible se branche par trois variables d'environnement.
+ Testé contre un double HTTP (`httpx.MockTransport`) qui exerce le VRAI client (délai, 429, 5xx, 4xx, JSON corrompu).
− La qualité d'Apertus sur nos tâches n'est **pas mesurée** : `eval/eval_apertus.py` le fera avec des identifiants ;
  sans eux, il écrit « NON EXÉCUTÉ ». Le produit ne dit jamais « Propulsé par Apertus » sans appel réussi.

Preuves : `tests/test_frontiere_ia.py`, `eval/resultats_apertus.md`.
