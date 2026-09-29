# Mémo benchmarks (travail) — ce que chaque chiffre prouve, et ce qu'il ne prouve pas

Tous les benchmarks ci-dessous tournent sur des données GÉNÉRÉES par nous (SYNTHETIC). Aucun ne dit ce que feraient de
vrais membres du Club. La « vérité » cachée est notre construction : un biais de conception est possible.

## 1. Plan de soirée (`eval/benchmark_reseau.py`)
Même ensemble de candidats et même budget pour toutes les méthodes (biais d'équité corrigé, FAILURES n° 8).
Optimiseur : 95,7 % de ponts, 37,4 membres servis ; PERD sur la réciprocité face à la méthode qui ne vise qu'elle
(16,3 % contre 17,8 %). Front de Pareto non dégénéré (3 à 10 points, médiane 9).

## 2. Intervention minimale (`eval/benchmark_interventions.py`, idée I-01)
20 réseaux de 150 membres ; budget 10 actions ; plafond 1 sollicitation par membre ; mêmes candidates.

| Méthode | isolés reliés | plus grand groupe | valeur des aides | réciproques |
|---|---|---|---|---|
| INCLUSION | **10,15** | 34,70 | 12,75 | 2,75 |
| COHÉSION | 0,90 | 56,25 | 13,65 | 3,70 |
| Ablation V1 (isolés d'abord) | 18,00 | 26,90 | 11,97 | 2,00 |
| Preuve d'abord | 6,45 | 36,40 | **17,15** | **7,15** |
| Populaires | 0,10 | **57,75** | 10,30 | 0,50 |
| Hasard (30 tirages) | 6,75 | 37,24 | 10,13 | 0,79 |

Lecture honnête :
- INCLUSION relie le plus de membres sans relation actuelle (20/20 réseaux contre les baselines).
- COHÉSION NE BAT PAS « populaires » sur la taille du plus grand groupe (56,3 contre 57,8 ; 8/20 réseaux), mais avec
  7 fois plus d'actions réciproques. On ne peut pas dire « notre méthode connecte mieux le réseau ».
- « Preuve d'abord » gagne sur la valeur des aides et la réciprocité : c'est ce qu'elle optimise.
- Inclusion et cohésion sont en conflit : le produit présente les deux plans et l'humain choisit.
- **Effet de second ordre trouvé** : l'ablation V1 relie 18 isolés mais en îlots de deux (plus grand groupe 26,9) ;
  deux nouveaux venus reliés entre eux n'ont personne pour les présenter plus loin. Corrigé dans INCLUSION (un isolé
  est relié au réseau vivant), testé (`test_interventions.py`).

## 3. Montée en charge (`eval/perf_echelle.py`) — voir `eval/resultats_perf_echelle.md`
Relances à 500 membres : 20,8 s → 0,49 s après correction (FAILURES n° 24). 5000 membres : 5,3 s (tâche de fond).

## Règles tenues
Mêmes candidats et même budget pour toutes les méthodes ; défaites publiées ; hypothèse « toutes les actions
acceptées » écrite dans chaque sortie ; jeux réservés jamais réutilisés pour régler.
