# SYNTHETIC BENCHMARK — Club Pulse

Données **SYNTHÉTIQUES** : 20 clubs générés (tailles [150, 500], graines 1–10), vérité terrain plantée. Aucun modèle de langage. Résultats déterministes (rejouables à l'octet). Ce banc mesure le respect des règles et la robustesse aux pièges — **pas** la pertinence humaine ni un impact.

## 1. Détection des situations plantées

| Type | Trouvées / plantées |
|---|---|
| COMPLEMENTARITE | 40 / 40 |
| COMPOSITION | 20 / 20 |
| CONVERGENCE | 20 / 20 |
| LACUNE | 20 / 20 |
| LATENTE | 40 / 40 |
| mémoire du Club | 20 / 20 |

### Pièges : combien de fois la paire interdite est-elle proposée ?

| Piège | Moteur | Appariement par capacité | Ressemblance de profils |
|---|---|---|---|
| AUCUNE_LANGUE_COMMUNE | 0 / 20 | 20 / 20 | 0 / 20 |
| CONCURRENT | 0 / 20 | 20 / 20 | 0 / 20 |
| DEJA_EN_RELATION | 0 / 20 | 20 / 20 | 0 / 20 |
| INDISPONIBLE | 0 / 20 | 20 / 20 | 0 / 20 |
| INTRODUCTION_DECLINEE | 0 / 20 | 20 / 20 | 0 / 20 |
| MEME_ORGANISATION | 0 / 20 | 20 / 20 | 0 / 20 |
| PROFIL_OBSOLETE | 0 / 20 | 20 / 20 | 0 / 20 |
| REFUS_INTRODUCTIONS | 0 / 20 | 20 / 20 | 0 / 20 |
| RESSEMBLANCE | 0 / 20 | 0 / 20 | 10 / 20 |
| **total** | **0 / 180** | **160 / 180** | **10 / 180** |

Opportunités détectées par club (moyenne) : 57.5 — leur précision sur le FOND n'est pas mesurable (aucune vérité terrain hors situations plantées).

## 2. Adaptation après une perturbation (banc d'essai)

240 essais proposés depuis une opportunité détectée ; la personne invitée accepte (elle déclare 60 min) puis se retire (121) ou n'a plus que 20 min (119). Oracle : règles réécrites et appliquées par force brute à toutes les offres volontaires publiques (synthétiques, dont des offres trop courtes, expirées, à venir ou d'une autre capacité). 0 publication(s) refusée(s).

| Mesure | Résultat |
|---|---|
| Remplacement proposé quand l'oracle en trouve un (complétude) | 118 / 118 |
| Remplacements proposés admissibles selon l'oracle (justesse) | 187 / 187 |
| Sans remplacement possible : arrêt propre (IMPOSSIBLE) ou raccourcir avec la même personne | 122 / 122 |
| « Raccourcir avec la même personne » proposé après une réduction | 119 / 119 |
| Personne retirée redésignée après adaptation | 0 |

## 3. Confidentialité

| Contrôle | Résultat |
|---|---|
| Identités (nom, courriel, organisation) dans ce que voit le moteur — 150 membres | 0 fuite(s) sur 450 contrôles |
| Identités (nom, courriel, organisation) dans ce que voit le moteur — 500 membres | 0 fuite(s) sur 1500 contrôles |
| Écrans de chaque membre et de la console (150 membres, 767 écrans, 1 refus) : nom de qui a décliné (hors la personne qui l'a invité), note privée d'autrui, observation non partagée, pseudonyme non rendu, identifiant interne | 0 fuite(s) |

## 4. Mémoire

Situation plantée : deux membres déclarent la même capacité ; l'un a déjà aidé (contribution confirmée par les deux parties et partagée avec le Club), l'autre a un profil plus récent et passerait devant sans mémoire.

- retrouvée avec la mémoire : 20 / 20 ;
- la même situation SANS la mémoire n'est pas retrouvée (la mémoire est décisive) : 20 / 20.

## Ce que ce banc ne dit pas

- rien sur de vrais membres, une vraie adoption ou un impact mesuré ;
- rien sur la qualité d'un modèle de langage (aucun n'est appelé) ;
- le générateur et le moteur partagent la taxonomie : un piège que la taxonomie ne sait pas exprimer n'est pas testé.
