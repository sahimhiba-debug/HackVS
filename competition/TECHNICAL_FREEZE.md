# Gel technique — preuves par critère

**Statut : GEL CONFIRMÉ au commit `7cfd076`** (CI verte : run 33 ; document : run 34). Après le gel, seuls sont
permis : corrections de défauts critiques (avec test rouge d'abord), réenregistrement de la vidéo, mise à jour du pitch
à partir des chiffres PROUVÉS (le validateur des affirmations reste en CI).

| # | Critère | Preuve | État |
|---|---|---|---|
| 1 | Architecture auditée | `ARCHITECTURE_MEMO.md`, `TECHNICAL_AUDIT.md` (cartographie statut / preuve / tests / risques) | ✓ |
| 2 | Code audité | lint vert ; 104 alertes mypy examinées, aucune atteignable ; garde défensive ajoutée | ✓ |
| 3 | Confidentialité | k-anonymat des refus, réponse uniforme, vue membre = ses relations ; `test_confidentialite_reseau.py`, `test_scene.py` | ✓ |
| 4 | Sécurité | matrice tiers × transitions, double soumission, erreurs sans trace ni SQL, entrées bornées + introspection (`test_securite_api.py`) | ✓ (authentification réelle absente : déclarée) |
| 5 | Graphe | historique ≠ actuel (`graphe_actuel`), propriété sur 100 historiques générés (`test_temporel.py`) | ✓ |
| 6 | Temporel | états dérivés des faits, refus ancien vs récent, frontière 9/10 jours, collisions d'événements (`test_collisions.py`) | ✓ |
| 7 | Optimiseur | 20/20 scénarios (`eval_decisions.py`), refus non levable (problème + validateur + gardien), « valide mais absurde » (`test_humain.py`) | ✓ |
| 8 | Matching | 112 cas : 43 WIN / 6 LOSS / 47 égalités justes / 16 égalités fausses ; abstentions 25/26 (`resultats_benchmark_categories.md`) | ✓ (défaites publiées) |
| 9 | Abstention | S09, abstention sans preuve (scène étape 5), NE_RIEN_FAIRE des interventions | ✓ |
| 10 | Simulation | `reseau.simuler` et `interventions.plan` : nature SIMULATION, aucune écriture (empreinte identique, testé) | ✓ |
| 11 | Rejeu | scène rejouée 3× à l'identique ; rejeu d'une décision APRÈS redémarrage réel du processus (`test_redemarrage.py`) | ✓ |
| 12 | Performance mesurée | 50 → 5000 membres générés (`resultats_perf_echelle.md`) ; test de complexité (lectures mémoire constantes) | ✓ |
| 13 | Tests adversariaux | matrice des 30 scénarios : 28 couverts, 2 partiels (preuves contradictoires, prompt malveillant), 0 non couvert | ✓ |
| 14 | Modes de défaillance | `FAILURE_MODES.md` (détection → reprise → impact → test pour chaque ligne) | ✓ |
| 15 | Benchmarks attaqués | biais d'équité corrigé (FAILURES 8) ; ablation montrant un effet de second ordre ; défaites publiées (`BENCHMARK_MEMO.md`) | ✓ |
| 16 | Idées explorées | `IDEA_BACKLOG.md` : 10 idées, verdicts KEEP / DEFER / REJECT argumentés | ✓ |
| 17 | Documentation synchronisée | `16_LIMITATIONS`, `13_QA_JURY`, `ADVERSARIAL_MATRIX`, mémos ; registre des preuves vérifié (`validate_competition_claims.py`, en CI) | ✓ |
| 18 | CI verte | runs 21–29 verts ; `6c07098` rouge (lint : ligne trop longue, poussée par erreur) corrigé par `e676ce2` ; run 33 (`7cfd076`) et 34 (`b96a59d`) verts | ✓ |
| 19 | Aucune faiblesse critique connue | 30 défauts réels trouvés et corrigés, chacun avec son test (`FAILURES.md`) ; limites restantes déclarées ci-dessous | ✓ |

## Limites connues, acceptées pour le gel (non critiques pour une démonstration FICTIVE)
- Pas d'authentification réelle ; vues d'organisation ouvertes en démo ; le mode réel refuse tout (testé).
- Aucun LLM vérifié contre une API réelle ; le produit n'en dépend pas.
- Analyse par règles : paraphrases et langues libres (22 / 112 échecs).
- Hypothèses de produit non mesurées : 90 jours, demi-vie de 30 jours, 3 relances par jour.
- Tous les benchmarks sont SYNTHÉTIQUES : ils ne prédisent pas le comportement de vrais membres.

## Ce qui se débloque après le gel
- Réenregistrer la vidéo (l'actuelle date d'avant les cycles 1–8 : `VIDEO_MEMO.md`).
- Mettre à jour le pitch à partir des chiffres prouvés uniquement ; aucune affirmation ne doit contredire le comportement réel.
