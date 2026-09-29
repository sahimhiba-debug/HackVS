# Frontière de Pareto des interventions — SYNTHETIC

20 réseaux GÉNÉRÉS de 150 membres ; budget 10 actions ; plafond 1 ; 15 pondérations + 4 plans heuristiques + 30 plans aléatoires d'exploration ; contrôle : 10 tirages aléatoires DISTINCTS, hors du vivier.

- Taille du front (plans non dominés) : médiane 9.0, min 4, max 15 ; plans distincts explorés : médiane 42.0.
- Un plan atteint l'idéal sur les 3 axes à la fois : 0/20 réseaux.
- Part des actions candidates qui relient deux secteurs différents : 97% (d'où l'abandon de la diversité sectorielle comme axe) ; sans aucun contact commun : 99% (non-redondance abandonnée).
- Plans nommés distincts (extrêmes + équilibre, doublons fusionnés) : médiane 3.0.

## Corrélation de rang entre objectifs, sur les plans du front (moyenne ; négatif = conflit)

| Paire d'objectifs | Spearman moyen | Réseaux (front ≥ 3) |
|---|---|---|
| inclusion × cohesion | -0.93 | 20 |
| inclusion × reciprocite | -0.15 | 20 |
| cohesion × reciprocite | -0.02 | 20 |

## Plans simples dominés par au moins un plan du front

| Plan | Dominé |
|---|---|
| INCLUSION (cycle 6) | 13/20 |
| COHESION (cycle 6) | 11/20 |
| PREUVE_D_ABORD | 17/20 |
| POPULAIRES | 15/20 |
| HASARD de contrôle (10 tirages × 20 réseaux, hors vivier) | 181/200 |

Hypothèse : toutes les actions acceptées. Un plan non dominé n'est pas « meilleur » : il est un compromis que l'humain choisit.
