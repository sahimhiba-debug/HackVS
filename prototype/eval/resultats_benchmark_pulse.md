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
| MEMOIRE | 20 / 20 |

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

## 2. Replanification après un refus

240 refus provoqués (le premier contributeur sollicité décline). Oracle : règles dures réécrites et appliquées par force brute à tous les membres, budget d'attention compris.

| Mesure | Résultat |
|---|---|
| Alternative proposée quand l'oracle en trouve une (complétude) | 198 / 198 |
| Alternative proposée éligible selon l'oracle (justesse) | 198 / 198 |
| Abandon propre quand il n'existe aucune alternative | 42 / 42 |
| Personne ayant décliné sollicitée à nouveau | 0 |

## 3. Confidentialité

| Contrôle | Résultat |
|---|---|
| Identités (nom, courriel, organisation) dans ce que voit le moteur — 150 membres | 0 fuite(s) sur 450 contrôles |
| Identités (nom, courriel, organisation) dans ce que voit le moteur — 500 membres | 0 fuite(s) sur 1500 contrôles |
| Nom d'une personne qui a décliné, ou note privée d'autrui, dans les écrans d'un autre membre — 150 membres, 754 écrans, 1 refus | 0 fuite(s) |

## 4. Mémoire

Situation plantée « déjà résolue dans le Club » retrouvée : 20 / 20.

## Ce que ce banc ne dit pas

- rien sur de vrais membres, une vraie adoption ou un impact mesuré ;
- rien sur la qualité d'un modèle de langage (aucun n'est appelé) ;
- le générateur et le moteur partagent la taxonomie : un piège que la taxonomie ne sait pas exprimer n'est pas testé.
