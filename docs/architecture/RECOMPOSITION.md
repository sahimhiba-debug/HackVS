> **HISTORIQUE — rédigé avant le registre des capacités (28–30.09.2026).** Conservé pour la traçabilité des décisions ; ne décrit PAS le produit actuel, et ses chiffres, routes et noms de fichiers peuvent être faux aujourd'hui. État actuel : [README](/README.md) · [index de la documentation](/docs/README.md).

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

## 11. Journal de la recomposition (ce qui a été fait, vérifié, et comment revenir en arrière)

| Étape | Commit | Vérification |
|---|---|---|
| 1. `explication.py` — « pourquoi » structuré | `c633736` | `tests/test_pourquoi.py` |
| 2. `essai.py` — gestes sur invitation, `origine` | `41b110e` | `tests/test_essai.py` (invitation, 60 → 20 min, éligibilité) |
| 3. `memoire_club.py` + boucle | `497c34f` | `tests/test_boucle.py` (découverte suivante ; mémoire contestée, négative, non partagée : rien) |
| 6a. Propriétés de l'ancien moteur PORTÉES sur le banc | `bca6f83` | `tests/test_essai_invariants.py` (10 invariants, 12 marches) ; oracle d'adaptation (`eval/benchmark_pulse.py`) |
| 6b. Retrait de l'ancien moteur | commit suivant | suite complète, bout en bout, `make quality-check` |

**Modification destructive (6b) — protocole suivi.**
1. *État sauvegardé* : `bca6f83` (tout l'ancien moteur y est intact, propriétés déjà portées).
2. *Raison* : deux moteurs d'activation, deux mémoires et deux consoles pour un seul produit (§5) ; l'ancien moteur
   n'était plus atteint par l'interface depuis le pivot ; le garder aurait maintenu 1 048 lignes et 23 routes sans
   usage, et une mémoire (« motifs ») que rien de vivant n'écrivait.
3. *Tests* : avant retrait, chaque propriété utile avait son équivalent sur le banc — invariants par marches
   aléatoires (`test_essai_invariants.py`), oracle par force brute (adaptation, 121/121 complète, 185/185 juste),
   audit de confidentialité des écrans (réécrit sur la nouvelle boucle : 763 écrans, 0 fuite, et un test prouve qu'il
   attrape une fuite réintroduite). Les tests de l'ancien moteur ont été retirés AVEC lui ; ceux de l'API ont été
   réécrits sur la boucle recomposée (mêmes intentions : session, autorisation, concurrence, refus jamais attribué,
   notes privées, injection, effacement).
4. *Retour arrière* : `git revert` du commit de retrait, ou `git checkout bca6f83 -- prototype/intelligence/activation.py …`.

**Retirés** : `intelligence/activation.py` (moteur), `intelligence/vues.py` (ses vues), `intelligence/apprentissage.py`
(« motifs »), l'ancienne démonstration en 10 étapes, les routes `/moi/pouls`, `/moi/opportunites/*`,
`/moi/sollicitations/*`, `/moi/activations/*`, `/moi/evenements`, `/memoire*`, `/console` (tour), `/console/scan`,
`/console/opportunites/*/activer|ecarter`, `/console/activations/*`.
**Ajoutés** : `vues_intelligence.py` (profil, notes, DÉCOUVERTES rendues par spectateur, panneau d'intelligence),
une démonstration en 11 étapes sur la boucle réelle, les routes `/moi/decouvertes[/{id}[/en-clair|/essai]]`,
`/console/intelligence`, `/console/decouvertes/{id}`.
**Convertis** : la détection lit la mémoire du banc (une contribution confirmée et partagée fait passer devant la
personne qui a déjà aidé — et seulement grâce à elle : vérifié « avec / sans mémoire ») ; le club synthétique plante
un souvenir au lieu d'un motif ; l'observateur ne lit plus de motifs ; le banc reçoit les règles dures du réseau
(`Etat.exclusion`) ; la version de l'analyse inclut le journal du banc.

**Trouvé en chemin (corrigé)** : un geste de compétence pouvait être « remplacé » par n'importe quelle compétence
(capacité déclarée désormais portée par le geste et l'offre) ; la passerelle échouait au-delà de 4 personnes ;
`Banc.offres()` était quadratique ; la note privée exposait à sa propriétaire l'identifiant interne de la personne
mentionnée ; le « pourquoi » d'un essai recopiait un raisonnement pseudonymisé (MEMBRE-xxx) lu tel quel par les
invités ; le profil de Claudia (fictive) était un piège « profil obsolète » incompatible avec son rôle dans la scène.
**Limite connue** : un texte LIBRE écrit par un membre (observation, note) qui nomme une autre personne n'est pas
réécrit si cette personne exerce son droit à l'effacement.
