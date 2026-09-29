# Journal de recherche

| Date | Question | Source | Constat | Implication | Action |
|---|---|---|---|---|---|
| 2026-09-28 | Que font déjà les plateformes d'événements ? | recherche web (Swapcard, Grip, Brella ; sources dans 20_COMPETITIVE_ANALYSIS) | mise en relation par IA, rendez-vous, communauté au-delà de l'événement : déjà là | ce n'est pas notre différenciation | recentrer sur la vie de la relation, le consentement, le réseau entier |
| 2026-09-28 | Que dit la page publique du Club ? | extraits de recherche foireduvalais.ch (page non accessible depuis notre environnement) | deux formules (Amis, Affaires), année mi-août → mi-août, événements réservés dont une soirée « Wow », cartes supplémentaires non nominatives | les événements sont l'accélérateur ; le réseau vit entre eux | scène ancrée sur « après l'événement » ; statut UNVERIFIED pour les détails |
| 2026-09-28 | Le front de Pareto est-il réel sur nos données ? | mesure | 1 point sur la démo : aucun conflit d'objectifs | ne pas revendiquer du multi-objectif sans données qui l'exigent | benchmark à conflits contrôlés (3 à 10 points) |
| 2026-09-28 | Le réseau grandit-il avec les soirées ? | simulation sur 150 membres générés | 11 groupes → 1 en 3 soirées, mais rencontres utiles 91 → 74 → 52 | le vivier s'épuise sans besoins nouveaux | la relance fondée sur un besoin nouveau devient centrale |
| 2026-09-28 | Notre avantage d'utilité est-il réel ? | relecture du benchmark | les baselines recevaient d'autres candidats | l'avantage d'utilité était gonflé | mêmes candidats pour tous ; chiffre corrigé publié |
| 2026-09-28 | Que signifiait la « réciprocité » du moteur ? | lecture de `matching.py` | « cherche dans votre secteur », pas « vous pouvez l'aider » | explication contradictoire possible | réciprocité prouvée par le même moteur en sens inverse |
| 2026-09-28 | Un chemin chaud est-il neutre ? | lecture adversariale | révéler l'intermédiaire expose une relation d'un tiers | la confidentialité porte aussi sur les LIENS | présentation proposée d'abord à l'intermédiaire |
| 2026-09-28 | Où vivent les relations ? | audit | deux sources de vérité | incohérences garanties à terme | projection du magasin dans une mémoire unique |
| antérieur | L'IA locale envoie-t-elle des données ? | inspection réseau à l'import d'onnxruntime | télémétrie tierce active par défaut | un appel externe non documenté | télémétrie coupée et testée (docs/EVALUATION.md §7) |
| antérieur | Une annonce « anonyme » est-elle anonyme ? | mesure sur le club de démonstration | 26 membres sur 34 ré-identifiables | l'anonymat par simple masquage ne suffit pas | besoins anonymes jamais projetés ; travail « intentions scellées » (docs/STRATEGIC_RESEARCH.md) |

Réponses prêtes :
- *Pourquoi un solveur ?* AD-05. *Pourquoi un graphe temporel ?* AD-01. *Pourquoi l'IA ne décide pas ?* AD-09.
- *Pourquoi le consentement ainsi ?* AD-07, AD-08 + la ligne « chemin chaud » ci-dessus. *Pourquoi pas du matchmaking ?* la
  première ligne de ce journal : il existe déjà ; notre valeur est après.

## Campagne finale (29.09.2026)
- La démo racontait trois démonstrations concurrentes → UNE histoire en 11 étapes ; l'abstention (« je pourrais
  inventer une connexion ») devient le moment de surprise, calculé par le moteur (15 possibles, 0 fondée).
- La saturation des soirées, découverte plus tôt, devient une étape : 9 → 1 → 0 puis abstention.
- « distribution » était de la logistique : faux positifs ; devenu un terme ambigu résolu par indices (AD-03).
- Deux sources de vérité (besoins comptés deux fois), un deck obsolète, des temps publiés périmés, une métrique de
  benchmark ambiguë : trouvés et corrigés (FAILURES n° 42–47).

