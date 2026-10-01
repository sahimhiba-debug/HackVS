# Latence réelle d'Apertus — mesure technique (séparée de la démonstration)

> Produit par `make latence-ia` (`prototype/scripts/mesurer_latence_apertus.py`). La démonstration n'appelle AUCUN
> modèle : elle tourne en forme déterministe. Cette mesure ne dit rien de la qualité des sorties.

## Contexte exact

- Période : 2026-10-01T19:47:52+00:00 → 2026-10-01T19:50:54+00:00 (UTC) ; commit `c11a386`
- Endpoint : `https://api.inference.cscs.ch/v1/chat/completions` (API d'inférence CSCS, compatible OpenAI) ; modèle `swiss-ai/Apertus-v1.5-70B`
- 30 appels mesurés par profil + 1 échauffement exclu ; séquentiels ; aucune nouvelle tentative ; délai 30.0 s (celui du produit)
- Client : Python 3.11.15, Linux-6.18.44-fc-v50-x86_64-with-glibc2.39, 4 processeurs, charge [0.0, 0.32, 0.56] ; réseau via le proxy HTTPS sortant de l'environnement
- Profil « tâche du produit » : `comprendre_action` (prompt `comprendre_action_v1`, schéma strict, `max_tokens` 900), 5 formulations fictives
- Profil « court » : une question d'une ligne, sortie json_schema d'un champ (`max_tokens` 60)

## Résultats (millisecondes, appels réussis seulement)

| Mesure | n | moyenne | médiane | p95 | min | max |
|---|---|---|---|---|---|---|
| Tâche du produit — HTTP (envoi → réponse complète) | 30 | 5434.4 | 5329.2 | 6021.2 | 4862.9 | 6105.4 |
| Tâche du produit — bout en bout (dont validation) | 30 | 5435.7 | 5330.7 | 6022.3 | 4864.0 | 6106.4 |
| Court — HTTP | 30 | 429.6 | 425.9 | 458.4 | 417.7 | 468.3 |

## Erreurs et sorties

- Tâche du produit : 30/30 réussis ; 0 erreur(s) HTTP ; 0 délai(s) dépassé(s) ou erreur(s) réseau
- Sorties validées par le produit : 0 acceptées, 30 rejetées (→ repli déterministe) — causes : capacité hors catalogue; geste ou durée hors bornes; structure inattendue
- Court : 30/30 réussis ; 0 erreur(s) HTTP ; 0 délai(s) ou erreur(s) réseau
- Jetons produits par appel (tâche) : médiane 355.0, p95 400.0, max 400.0
- Échauffement (exclu) : tâche 6001.0 ms, court 426.2 ms

Mesures brutes, appel par appel : `docs/audit/latence_apertus.json` (statut, durées, jetons — ni clé ni contenu).
