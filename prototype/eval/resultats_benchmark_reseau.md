# SYNTHETIC_BENCHMARK — recommandation de connexions : optimiseur vs baselines

**Données générées** (graines [1, 2, 3, 4, 5], 60 membres, 4 communautés, 6 membres « populaires », 8 nouveaux sans relation, 20 % d'offres périmées, 10 % sans consentement). **Aucune donnée du Club.** Budget : au plus 2 introductions par membre, pour toutes les méthodes. Moyennes sur 5 réseaux.

Utilité et réciprocité sont mesurées contre la vérité LATENTE (offres réellement valides), que personne ne voit.

| Méthode | Intros | Utiles % | Réciproques % | Membres dont un besoin est servi | Ponts % | Nouveauté % | Isolés restants | Nouveaux servis | Vers populaires % | Composantes | ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| aléatoire | 47.2 | 85.4 | 2.2 | 32 | 82.8 | 91.4 | 1.4 (sur 11.2) | 7.4 | 21.6 | 2.4 | 0.2 |
| similarité | 47.4 | 84.8 | 12.6 | 33.6 | 67.7 | 88.2 | 1.8 (sur 11.2) | 6.8 | 20.2 | 2.8 | 0.8 |
| pertinence gloutonne | 48.4 | 87.2 | 13.1 | 34.4 | 86.3 | 90.3 | 2 (sur 11.2) | 6.6 | 22.3 | 3 | 0.4 |
| réciprocité gloutonne | 47.6 | 88.6 | 17.8 | 35 | 86.0 | 90.6 | 2.4 (sur 11.2) | 6.2 | 22.6 | 3.4 | 0.7 |
| graphe (ami d'ami) | 47.2 | 85.3 | 10.3 | 32.2 | 70.5 | 64.6 | 2.8 (sur 11.2) | 6 | 22.4 | 3.8 | 1.2 |
| optimiseur (plateforme) | 52.2 | 89.3 | 16.3 | 37.4 | 95.7 | 95.0 | 1 (sur 11.2) | 7.4 | 20.6 | 2 | 427.4 |

Frontière de Pareto (points supportés, 4 objectifs) : [9, 3, 6, 9, 10] points selon le réseau (médiane 9).
