# Recomposition — Network Intelligence → Activation Engine → Memory

> Établi le 2026-09-29 en lisant le code (commit `abc2dc6`), pas les anciens rapports. `docs/CURRENT_STATE.md` date
> du 28.09 et décrit le prototype d'avant : il est **périmé** (signalé, non réécrit). Référence avant recomposition :
> `make quality-check` vert — 486 tests + 5 de bout en bout, lint et types propres, CI verte (runs 83–85).
> Chemin de retour : le commit `abc2dc6` (tout ce qui suit est additif ou fait l'objet d'un commit dédié et justifié).

## 1. Carte actuelle (ce qui existe réellement)

| Module (`prototype/intelligence/`) | Lignes | Rôle réel | Couche |
|---|---|---|---|
| `identite.py` | 239 | coffre d'identités, pseudonymes, codes d'invitation, `nettoyer` | Identité |
| `acces.py`, `reglages.py` | 70 | sessions HMAC, configuration | Identité |
| `politique.py` | 126 | portées, rendu par spectateur, k-anonymat | Politique |
| `observateur.py` | 161 | état observé du réseau (offreurs, recherches, relations, déclinées, événements proches) | **Network Intelligence** |
| `detection.py` | 501 | 8 familles d'opportunités, signaux sourcés, raisonnement, risques, confiance, rang | **Network Intelligence** |
| `modele.py` | 107 | `Reseau`, `Signal`, `Role`, `Opportunite` | Domaine NI |
| `apprentissage.py` | 83 | « motifs vérifiés » écrits par l'ANCIEN moteur, relus par la détection | Mémoire (ancienne) |
| `activation.py` | 627 | **ANCIEN moteur d'activation** (machine d'états, accords par étape, replanification) | Activation (doublon) |
| `vues.py` | 338 | vues de l'ancien moteur et du fil d'opportunités | Vues |
| `essai.py` | 647 | **Activation Engine** : offres, protocole versionné, accords par portée, adaptation, observation, réutilisation | **Activation** |
| `vues_essai.py` | 290 | vues par personne du banc d'essai + console légère | Vues |
| `ia.py` | 464 | `Intelligence` : Apertus ou repli déterministe, sorties validées | IA |
| `club_pulse.py` | 465 | service : état du monde, commandes des deux moteurs, notes, préparation IA | Composition |
| `club_synthetique.py`, `monde_demo.py`, `demo.py` | 458 | mondes fictifs, démonstrations | Démo |

API : `app/pulse_api.py` (38 routes : ancien parcours + console + démo) et `app/essai_api.py` (banc d'essai).

## 2. Ce qui reste de Network Intelligence
Complet et testé, mais **hors du parcours visible depuis le pivot** : `observateur` + `detection` trouvent des
opportunités prouvées (signaux cités mot pour mot, règles dures, pièges évités 0/180 sur un jeu auto-construit), avec
raisonnement, risques et confiance. **Il manque** : une explication STRUCTURÉE (besoin, capacité, contexte, relation,
moment, consentement, preuves, inconnues, risques) ; la distinction « capacité déclarée » ≠ « disponibilité connue » ;
l'usage de la mémoire du banc d'essai.

## 3. Ce qui est devenu Activation Engine
`essai.py` : c'est le moteur retenu. **Limite actuelle** : il n'accepte que des gestes adossés à une OFFRE publiée —
il ne sait pas recevoir une opportunité détectée où la personne pertinente n'a pas (encore) offert de disponibilité.

## 4. Interfaces entre les deux — aujourd'hui : AUCUNE
La détection alimente l'ANCIEN moteur (`ClubPulse.activer` → `Moteur`), pas le banc d'essai. Le banc d'essai ne sait
rien des opportunités. La mémoire du banc (observations, droits) n'est lue par personne d'autre.

## 5. Doublons (à résoudre, pas à cacher)
| Doublon | Garder | Retirer | Condition |
|---|---|---|---|
| Deux moteurs d'activation : `activation.Moteur` / `essai.Banc` | `essai.Banc` | `activation.py`, ses routes, ses vues, l'ancienne démo en 10 étapes | propriétés utiles PORTÉES sur le banc avant suppression : invariants par marches aléatoires, oracle de replanification, audit de confidentialité des écrans |
| Deux mémoires : motifs (`apprentissage`, écrits par l'ancien moteur) / observations + droits (banc) | la mémoire du banc, projetée en « contributions vérifiées » | l'écriture de motifs par l'ancien moteur | la détection lit la nouvelle mémoire (preuve + risque), seulement dans le périmètre autorisé |
| Deux consoles (JSON « tour » de l'ancien parcours / console du banc) | une salle de contrôle unique | l'ancienne tour | — |

## 6. Fonctions retirées du parcours visible qui DOIVENT revenir
- Le **fil d'opportunités** du membre — mais sous forme de « découvertes » expliquées, jamais un score.
- L'**explication** (« pourquoi elle / lui ? ») avec les preuves autorisées.
- Le **panneau d'intelligence** de la console (ce que le réseau pourrait faire, et pourquoi).
Ne reviennent PAS : scores de santé, graphe global, scan « spectacle » avec chronométrage.

## 7. Risques
1. Qu'une opportunité soit lue comme une DÉCISION : la détection ne doit jamais solliciter ; seul le bénéficiaire
   propose un essai (et chaque participant consent).
2. Qu'une capacité de profil soit prise pour une DISPONIBILITÉ : l'invité déclare sa disponibilité EN acceptant.
3. Qu'une mémoire devienne une réputation (« Markus est fiable ») : la mémoire dit « dans ce contexte, cette
   contribution a été reçue et jugée utile par cette personne, avec ces limites » — contestable, bornée par les droits.
4. Fuite par la preuve : une explication cite une mémoire que le spectateur n'a pas le droit de voir.
5. Casse de tests en retirant l'ancien moteur : porter les propriétés AVANT de supprimer.
6. Réarchitecture de façade : déplacer des fichiers en `domain/ activation/ memory/…` coûterait des centaines de
   lignes d'imports sans comportement nouveau.

## 8. Architecture cible
```
 Identity Vault (identite, acces)  ──► profils PSEUDONYMISÉS
        │
        ▼
 NETWORK INTELLIGENCE   observateur → detection → explication (NOUVEAU, pur)        « il existe peut-être… »
        │                     ▲                        │
        │                     │ preuves + risques      ▼
        │               MEMORY (NOUVEAU, pur)     Opportunité expliquée  ──► le bénéficiaire DEMANDE (« proposer un essai ? »)
        │               = projection du journal         │
        │                 du banc : contributions       ▼
        │                 vérifiées, contestées,   PASSERELLE (NOUVEAU, petit) : opportunité → brouillon d'essai
        │                 bornées par les droits        │     (gestes « sur invitation » : aucune disponibilité supposée)
        │                     ▲                         ▼
        │                     └──────────────  ACTIVATION ENGINE (essai.py, inchangé dans ses règles, étendu :
        │                                        invitation → l'invité déclare sa disponibilité EN acceptant)
        ▼
 POLICY (politique, vues_essai, vues_intelligence) : ce qu'UNE personne voit ; révélation d'identité = règle, jamais inférence
 AI (ia.py) : Apertus | autre fournisseur compatible OpenAI | repli déterministe — brouillons seulement
```
**Pas de déplacement physique en paquets** (`domain/`, `activation/`…) : les couches sont des MODULES, et leur
direction de dépendances est vérifiée par `tests/test_architecture.py` (règles ajoutées : la détection n'importe pas
le banc ; le banc n'importe ni la détection ni la mémoire ; seule la passerelle connaît les deux). Un déplacement
physique ne changerait aucun comportement et casserait l'historique.

## 9. Boucle cible (signature)
MEMBRE → BESOIN → SIGNAUX → OPPORTUNITÉ (+ pourquoi) → ESSAI (consentements, versions) → PERTURBATION → ADAPTATION →
CONTRIBUTION → OBSERVATION → MÉMOIRE (bornée, contestable) → MEILLEURE DÉCOUVERTE SUIVANTE (preuve affichée, ou risque
si l'essai n'a pas aidé).

## 10. Plan (chaque étape : tests, types, lint, attaque, documentation, commit)
1. `explication.py` : « pourquoi » structuré, disponibilité connue/inconnue, consentement, preuves, inconnues, risques.
2. `essai.py` : gestes sur invitation (disponibilité déclarée par l'acceptation) ; `origine` du protocole.
3. `memoire_club.py` : projection « contributions vérifiées » ; la détection et l'explication la lisent (dans le
   périmètre autorisé) ; boucle démontrée par un test : essai confirmé → meilleure découverte suivante.
4. `passerelle.py` + API : découvertes du membre, « proposer un essai » depuis une opportunité.
5. Salle de contrôle : que se passe-t-il, pourquoi, ce qui bloque, ce qui a changé, ce qui a été appris ; panneau de
   perturbations du jury (règles réelles, gestes JOUÉS marqués).
6. Retrait de l'ancien moteur après portage des propriétés (commit dédié, justification, chemin de retour).
7. Banc d'évaluation en 8 dimensions ; interface ; présentation, vidéo hors ligne ; trois audits.
