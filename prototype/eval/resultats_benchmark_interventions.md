# Benchmark — intervention minimale (SYNTHETIC)

20 réseaux GÉNÉRÉS de 150 membres ; budget 10 actions ; plafond 1 sollicitation(s) par membre ; mêmes candidates pour toutes les méthodes. Moyennes par réseau.
Candidates par réseau : 520.2 ; membres sans relation actuelle avant : 48.7.

| Méthode | isoles_relies | plus_grand_groupe | valeur_aides | reciproques | actions |
|---|---|---|---|---|---|
| INCLUSION | 10.15 | 34.70 | 12.75 | 2.75 | 10.00 |
| COHESION | 0.90 | 56.25 | 13.65 | 3.70 | 10.00 |
| ABLATION_V1 | 18.00 | 26.90 | 11.97 | 2.00 | 10.00 |
| PREUVE_D_ABORD | 6.45 | 36.40 | 17.15 | 7.15 | 10.00 |
| POPULAIRES | 0.10 | 57.75 | 10.30 | 0.50 | 10.00 |
| HASARD | 6.75 | 37.24 | 10.13 | 0.79 | 10.00 |
- INCLUSION ≥ la meilleure baseline sur « isoles_relies » : 20/20 réseaux.
- COHESION ≥ la meilleure baseline sur « plus_grand_groupe » : 8/20 réseaux.
- INCLUSION ≥ la meilleure baseline sur « plus_grand_groupe » : 1/20 réseaux.
- COHESION ≥ la meilleure baseline sur « isoles_relies » : 0/20 réseaux.

ABLATION_V1 (isolés d'abord, sans regarder à quoi on les relie) : elle relie plus d'isolés mais crée des îlots de deux ; c'est l'effet de second ordre qui a motivé la version retenue.
Hypothèse : toutes les actions acceptées. Vérité : générée par nous (biais de conception possible).
