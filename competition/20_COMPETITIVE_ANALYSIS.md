# 20 — Analyse concurrentielle (factuelle, sans dénigrement)

Sources consultées le 2026-09-28 (recherche web ; les pages des éditeurs n'étaient pas toutes accessibles depuis notre
environnement — nous citons ce que les résultats de recherche décrivent, pas des tests des produits) :
- Swapcard : [fonctions IA](https://www.swapcard.com/blog/swapcard-ai-features), [mise en relation](https://www.swapcard.com/event-matchmaking-platform), [networking](https://www.swapcard.com/features/event-networking)
- Grip : [mise en relation IA](https://www.grip.events/products/event-matchmaking), [site](https://www.grip.events/)
- Brella : [mise en relation](https://www.brella.io/event-matchmaking), [associations](https://www.brella.io/associations), [site](https://www.brella.io/)

## Ce qui EXISTE déjà (ce n'est PAS notre différenciation)
| Capacité | Constat (sources ci-dessus) |
|---|---|
| Mise en relation par IA | Swapcard (intérêts, rôles, actions dans l'événement), Grip (nombreuses stratégies d'apprentissage, signaux de comportement), Brella (intérêts + intention) |
| Prise de rendez-vous 1:1 pendant l'événement | les trois |
| Communauté au-delà de l'événement | Swapcard (pages communauté) ; Brella (offre dédiée aux associations, engagement des membres) |
| Annuaire, messagerie, recommandations de sessions et d'exposants | les trois |

## Ce que NOUS faisons différemment (et que nous pouvons prouver)
| Dimension | Notre prototype | Preuve |
|---|---|---|
| Mémoire relationnelle temporelle | chaque rencontre, introduction, suivi, opportunité est un fait daté ; l'état de la relation en est dérivé | `plateforme/memoire.py`, `test_reseau.py` |
| Suivi seulement avec une raison prouvée | relance = besoin nouveau / réciprocité ouverte / présentation via un contact suivi ; sinon silence compté | scène, étape 9 ; `test_cycle.py` |
| Abstention de première classe | « Japon » : aucune proposition ; 20 scénarios de décision | scène, étape 5 ; `eval_decisions.py` |
| Explication = décision | explications recalculées et comparées par tests (mutation) | `test_explications.py` |
| Consentement relationnel | double accord ; présentation proposée d'abord à l'intermédiaire ; chemin d'un tiers jamais révélé | `test_reseau.py` |
| Optimisation au niveau du réseau | solveur sous contraintes (valeur collective, ponts, couverture) + simulation avant/après | benchmark SYNTHÉTIQUE, scène étape 12 |
| Aucune dépendance à une IA externe | fonctionne sans clé ; modèles externes déclarés, jamais « vérifiés » sans test réel | `/api/modeles` |

## Ce que nous ne savons PAS (et ne prétendons pas)
- Si les produits cités font du suivi post-événement fondé sur des preuves : non documenté dans les extraits consultés —
  **ce n'est pas une preuve d'absence**.
- Comment nos méthodes se comparent aux leurs sur de vraies données : aucune comparaison directe n'a été faite.

## Réponse à « Pourquoi pas LinkedIn ? »
LinkedIn est un réseau ouvert et public. Le Club est un réseau fermé, annuel, dont l'annuaire ne publie pas les
contacts (selon le brief) et dont la valeur naît d'événements précis. Notre architecture répond à ce contexte :
introductions consenties, relations datées et reliées aux événements du Club, besoins et offres des membres,
optimisation collective sous contraintes, simulation, boucle d'activation. Nous ne remplaçons pas LinkedIn ;
nous faisons vivre un réseau privé entre ses événements.

## Réponse à « Pourquoi pas Swapcard / Grip / Brella ? »
Ils excellent sur l'événement et la mise en relation. Si le Club les utilise, notre moteur peut s'y ajouter comme
couche de mémoire et de suivi (frontière MCP). Notre différence n'est pas « l'IA qui recommande », c'est ce qui se
passe après la recommandation — prouvé, consenti, et mesuré sur le réseau entier.
