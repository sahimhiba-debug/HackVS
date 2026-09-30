> ⛔ **OBSOLÈTE — produit d'avant le pivot, ne pas présenter.** Ce dossier décrit l'ancien produit (« intelligence relationnelle »), pas le registre des capacités. La réécriture du pitch est en cours (équipe) ; voir `TODO-DEMO.md`.

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

## 4. Matching par catégorie (`eval/benchmark_categories.py`) — 112 cas, 6 jeux écrits avant exécution
Moteur contre « mots-clés + mêmes filtres » : **43 WIN, 6 LOSS**, 47 égalités justes, 16 égalités fausses ; abstention
juste quand il le fallait 25/26. Le moteur échoue sur 22 cas, presque tous des PARAPHRASES (« ordis lents »,
« emprunt ») et des besoins rédigés en allemand ou en anglais libre (jeux réservés 3 et 4). Limite connue de l'analyse
par règles à vocabulaire fermé ; la couche sémantique optionnelle a ses propres résultats (`resultats_*_semantique.md`).
Les 6 défaites sont publiées ; les jeux réservés ne servent pas à régler.
Comportements (tests exécutés par le benchmark) : démarrage à froid, saturation, contradiction, échec de réciprocité
dit et non inventé, cohérence explication = décision → tous PASS.

## 5. Sprint d'innovation (détail : EXPERIMENT_LOG.md)
| Expérience | Résultat principal | Défaite / limite publiée |
|---|---|---|
| B Observatoire (10 cas × 20 graines) | rappel complet ; 0 fausse alerte sur réseau sain | baseline KPI : signale un changement mais ne nomme rien ; vieillissement non détecté à 21 % d'extinction |
| C/J Pareto 4 axes (20 réseaux) | aucun plan idéal (0/20) ; inclusion × cohésion ρ −0,72 ; cohésion robuste indépendante (−0,03) | diversité sectorielle et non-redondance abandonnées (constantes) ; front approché (167/200 plans aléatoires de contrôle dominés) |
| F Échéancier (20 réseaux, 30 j) | INCLUSION gagne 20/20 ; COHÉSION 18/20 (+2 égalités) | chacune perd sur le critère de l'autre ; 1re conception (90 j) dégénérée |
| G Sérendipité | 92 % des paires par similarité sans aide prouvée | hypothèse « la similarité enferme dans le secteur » RÉFUTÉE (86 % inter-secteurs) |
| J Cohésion robuste | groupe robuste 28,1 contre 6,7 ; ponts fragiles −4,4 contre +15,4 | plus grand groupe 34,6 contre 60,9 (la cohésion simple gagne sur son critère) |
| K Prévention robuste | — | PERD (2,30 contre 2,75) : DELETE |
| L Invitation ciblée (flot exact) | petite soirée : gagne 7, égalité 13, perd 0 (9,30 contre 8,65) | grande soirée : égalité 20/20 avec la règle simple |
| M Actions « maintenant » | 6 % des relations endormies ont une raison prouvée (silence pour 94 %) | « raison » = aide prouvée seulement |
| N Boucle sur 3 mois | bilan = acceptations EXACTEMENT (après correction d'une double attribution) | politiques de saison : non concluant |
| O Stabilité | INCLUSION 0,96 ; hystérésis 0,71 → 0,76 à coût borné | ÉQUILIBRE reste le moins stable (instabilité surtout structurelle) |

## Règles tenues
Mêmes candidats et même budget pour toutes les méthodes ; défaites publiées ; hypothèse « toutes les actions
acceptées » écrite dans chaque sortie ; jeux réservés jamais réutilisés pour régler.
