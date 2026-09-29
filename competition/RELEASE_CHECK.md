# Vérification de publication (campagne finale, 29.09.2026)

Règle : une étape n'est verte que si le CODE DE SORTIE de son processus est 0 (jamais celui d'un `tail` ou d'un tube).

| Étape | Commande | Résultat (code de sortie) |
|---|---|---|
| Suite de tests complète | `python -m pytest -q` | 276 réussis (0) |
| Lint | `ruff check .` | aucune erreur (0) |
| Contrôle de types | `python -m mypy app adaptateurs plateforme` | 0 erreur sur 50 fichiers (0) — 116 au départ, FAILURES n° 48 |
| Bout en bout, navigateur bureau + mobile | `pytest tests/test_e2e_scene.py` (obligatoire en CI) | réussi (0) ; CI : exécuté, pas ignoré |
| Réinitialisation, rejeu | `tests/test_scene.py` (rejeu ×3, clics simultanés, réinitialisation) | réussi (0) |
| Lisibilité de la démo | `python scripts/mesurer_scene.py` | ≤ 101 mots par étape, 0 % caché à 1440×900, attente < 200 ms, 0 erreur de console |
| Évaluations | `python -m eval.run_eval --verifier` ; `python -m eval.eval_decisions` | 112 cas inchangés (0) ; 20/20 (0) |
| Benchmarks rejoués à l'octet | `python scripts/reproduire_sprint.py` puis `git diff --exit-code -- eval/` | identiques (0) |
| Performance | diagnostic 150 / 500 / 1000 membres générés | 0,91 / 6,8 / 24,2 s (médianes de 3) ; limite déclarée |
| Registre des affirmations + pitch + deck + vidéo | `python scripts/validate_competition_claims.py` (complet, benchmark inclus) | tout vérifié (0) |
| Vidéo | durée = légendes (validateur) ; revue « spectateur novice » à 15 / 45 / 90 s / fin | 114 s, 14 plans, conforme au code |
| Secrets | recherche de clés dans chaque diff avant commit | aucune |
| CI GitHub | jobs `qualite` (lint, types, tests, évaluations, registre) et `reproductibilite` (E2E, benchmarks) | vert jusqu'au run 72 ; run du dernier commit : voir l'onglet Actions |

## Ce qui reste ouvert (et le restera sans décision ou ressource externe)
- **IA générative** : aucun modèle accessible depuis l'environnement ; bancs G1/G2 prêts, NON EXÉCUTÉS. Retirée de la démo.
- **Valeur réelle** : aucune donnée ni aucun utilisateur réel ; protocole de pilote écrit (VALEUR_METIER § 6).
- **Brief et règlement officiels** : non reçus ; temps de présentation non confirmé (10_PITCH : versions 90 s, 3 min, 5 min).
- **Sources concurrentielles** : pages éditeurs bloquées ; matrice fondée sur des extraits de recherche (AUDIT § 7).
