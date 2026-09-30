# Phase 2 — Activation : compte rendu de sortie

> Branche `claude/modest-bohr-xvk53n`, de `b5d6237` (Phase 1 validée) à ce commit. Chemins relatifs à `prototype/`.
> **F** = fait vérifié par une commande ou un test · **H** = jugement.
> Critère de sortie : *retrait → dégradation → recomposition vérifiable, retrait anonyme* — plus vos reports : cas 3
> et 7, levier dérivé du compositeur (I1), HypotheticalClaim / status_if (I3), non-régression du compositeur, capture
> d'artefacts E2E, complexité du retour arrière, plafond d'Ask, concurrence, écrans, TODO-DEMO.

## 1. Verdict

**Critère de sortie atteint (F).** Par l'API, avec de vraies sessions (`tests/test_capacites_retrait.py`), puis dans
Chromium (`tests/test_e2e_capacites.py`) :
1. Pauline comble la capacité, qui devient `ACTIVE` ; son reçu est sur son téléphone.
2. Elle retire son consentement en un geste.
3. À la projection suivante, la capacité est `DEGRADED`, et la recomposition est calculée par le compositeur partagé
   (ici, une nouvelle demande).
4. L'Établi dit « transport : ce composant n'est plus disponible », sans nom, sans raison, sans le mot « retiré ».
5. La demande repart vers Markus, jamais vers elle. Markus répond, et la capacité est de nouveau `ACTIVE`.

Rejoué **10 fois de suite : 10/10** (§ 5).

## 2. Commits (un sujet chacun ; chaque correctif a un test rouge d'abord)

| Commit | Nature | Rouge sur l'ancien code (pour la bonne raison) |
|---|---|---|
| `a5bc176` security(frontiere) | texte libre lu par le moteur (profil, besoin, offre, réponse) nettoyé des identités du coffre, **son propre nom compris** | `test_frontiere_textes.py` : 5/5 rouges (noms, organisation, courriel, téléphone présents) |
| `ad5b724` ci(mutation) | mutation : à la demande, la nuit, par filtre de chemins, sur tag `demo-*` ; liste classée contrôlée | — |
| `fdc62e1` fix(composition) | mêmes entrées → mêmes équipes qu'avant le retour arrière ; budget de nœuds déclaré | `test_composition_non_regression.py` : 4 graines où l'équipe DIFFÉRAIT (registre) |
| `f368615` fix(adaptation) | cas 3 et 7 : compétence retirée, indisponible, non sollicitable → accords et consentements dégradés | `test_adaptation_profil.py` : 7/7 rouges (AUTORISE / ACTIVE) |
| `216679e` feat(capacites) | retrait de finalité, perte anonyme, recomposition / aucune solution sûre, reçus, Mes données | fonctionnalité ; le test d'anonymat a attrapé une fuite dans mon premier jet (§ 6) |
| `9461e5d` feat(capacites) | HypotheticalClaim / status_if (I3), levier et pièces critiques dérivés du compositeur (I1) | fonctionnalité, jugée par l'oracle |
| `cb2d0f6` feat(asks) | une Ask à la fois, levier d'abord, 7 jours de silence après une réponse ; une liaison sous concurrence | fonctionnalité ; test de concurrence vérifié non vacueux (§ 4) |
| `4dc38f6` feat(pulse) | Pulse par rejeu du journal | fonctionnalité |
| `fe0cce1` feat(ui) | Établi, Passeport, téléphone (Demandes, reçus, retrait, Mes données), capture E2E | fonctionnalité |
| *(ce commit)* test + docs | tests tueurs de mutants de la Phase 2, date sur chaque écran du téléphone, calendrier des scènes, ce compte rendu | — |

## 3. Ce qui existe maintenant (F)

- **Retrait** d'un consentement de finalité, en un geste (`POST /moi/capacites/{id}/retrait`).
  - La personne n'est ensuite ni liée ni sollicitée à nouveau pour cette finalité.
  - Les écrans disent « {rôle} : ce composant n'est plus disponible », jamais qui ni pourquoi. Les pertes sont
    ordonnées par emplacement du patron, pas par membre.
- **Recomposition**, calculée et jamais appliquée. Trois issues :
  - `consentir` : une autre pièce existe, son auteur décide ;
  - `demander` : une nouvelle Ask ;
  - « aucune solution sûre » : la cause (par rôle), ce qu'on sait, ce qu'on ignore, ce qui débloquerait.
- **Cas 3 et 7.** `Banc(membre_peut=…)` relit le profil à chaque couverture : disponible, sollicitable, et déclare
  encore la capacité. Le motif est unique et générique ; il ne dit pas lequel des trois.
- **HypotheticalClaim / `status_if`** (I3) : une superposition en lecture seule. Elle n'écrit rien (vérifié par
  l'empreinte du journal), ne réserve rien, ne consent à rien, et disparaît même sur erreur. Elle n'est jamais ACTIVE.
- **Levier** (I1) : le nombre de capacités qui passent à distance 0 avec la pièce demandée, calculé par `status_if`
  sur le compositeur partagé, sans boucle à part.
- **Pièces critiques** : contrefactuel par le compositeur, qui exclut les pièces des membres retirés.
- **Asks** : au plus une montrée à la fois, le levier le plus fort d'abord, puis l'expiration. Aucune nouvelle Ask
  pendant 7 jours après une réponse, oui comme non. Paramètres `Reglages.asks_montrees` et `plafond_jours`.
  Deux réponses concurrentes donnent une seule liaison.
- **Pulse** (`GET /console/pulse`) : apparues, éteintes, recomposées, fragiles, à une pièce près. Chaque côté est
  une réplique **rejouée** du journal (`ClubPulse.au(seq)`), sans fournisseur de langage.
- **Reçus** (`GET /moi/consentements`) et **Mes données** (`GET /moi/donnees`) : quoi, pourquoi, jusqu'à quand ; rien
  sur les autres membres.
- **Écrans.** `/etabli` (Établi et Passeport, bandeau « à l'attention de l'animation », Pulse). Téléphone : onglet
  « Demandes » et « Mes données ». **Chaque écran affiche sa date** : en-tête du téléphone sur tous ses écrans, Établi,
  et la projection et la console qui l'affichaient déjà. Chaque carte de capacité dit son jour.
- **Cache de projection** : la clé est ce dont la projection dépend (journal, profils, horloge, patrons) ; il rend
  une copie.
- **Capture sur échec E2E**, branchée une fois pour tous les E2E : capture d'écran, HTML et URL de chaque page ouverte,
  avant la fermeture du navigateur. La CI les publie comme artefact.
- **TODO-DEMO** : « redémarrage = nouvelle démo ». **DEMO_SCRIPT § 0** : le calendrier des scènes, un jour par scène.

### Complexité du retour arrière (dossier)
Une recherche d'équipe porte sur un créneau : au plus 4 gestes × les offres admissibles de chacun, en profondeur.
- **Ordre stable** : l'offre gardée d'abord, puis les candidats dans l'ordre du banc. Le premier chemin est l'ancien
  choix glouton.
- **Borne pratique** : quelques dizaines de nœuds dans la démo.
- **Garde** : `Banc.BUDGET_NOEUDS = 20 000` nœuds par créneau. Au-delà, la recherche s'arrête, `recherches_tronquees`
  compte l'arrêt, et le registre ajoute l'hypothèse « recherche bornée atteinte… absence non garantie ». Jamais un
  « impossible » silencieux.
- **Pire cas théorique** : O(n⁴) par créneau pour n offres admissibles par geste. À surveiller au-delà de quelques
  centaines d'offres actives.

## 4. Qualité (F)

- **Oracle** : levier et pièces critiques, sur 150 mondes à deux patrons, comparés à l'oracle en force brute
  (qui n'utilise pas le compositeur). Un garde vérifie que des leviers 1 et 2 et des pièces critiques apparaissent.
  Composition : 6 000 graines sans désaccord. Non-régression contre le glouton : 4 000 graines sans divergence.
- **Concurrence** : 10 exécutions de deux fils qui répondent à la même Ask par l'API donnent une liaison et un
  consentement. Contre-épreuve à la main : sans la relecture de l'Ask, les 10 exécutions échouent.
- **Rejeu** : l'empreinte de l'état rejoué à chacune de 5 positions égale celle capturée en direct à cette position
  (et les 5 empreintes diffèrent).
- **Mutation** sur `capacites.py`, campagne de fin de phase (le module a presque doublé) :

  | Campagne | Tués | Survivants | Non classés |
  |---|---|---|---|
  | début de campagne Phase 2 | 994 / 1 188 (83,7 %) | 194 | 152 → garde CI : **échec**, comme voulu |
  | après `test_capacites_regles_phase2.py` (12 tests) | **1 086 / 1 188 (91,4 %)** | 102 | **0** (tous classés équivalents) |

  Les survivants restants sont classés équivalents dans `docs/audit/mutants_survivants.txt`. Catégories :
  bornes `maximum` des recherches dont seul le premier résultat est lu ; `permis` redondant avec la liste des candidats
  publics ; clés internes d'empreinte et de lignes ; découpages de chaîne sans séparateur interne ; messages enveloppés.

## 5. Vérifications finales (2026-09-30)

| Contrôle | Résultat |
|---|---|
| `pytest` (hors E2E) | **1 125 passed** (905 à la fin de la Phase 1) |
| E2E Chromium (scène, Club Pulse, action collective, **registre**) | **8/8, deux fois de suite** ; aucune capture d'échec produite |
| ruff · mypy · secrets | propres · 76 fichiers sans erreur · aucun secret |
| `make eval` | vert |
| `scripts/reproduire_sprint.py` puis `git status eval/` | aucun écart : résultats publiés identiques à l'octet |
| Critère de sortie + scénario A, ×10 d'affilée | **10/10** |
| `make mutation` (registre) | 1 086 / 1 188 tués, 0 survivant non classé |
| Projection des 6 patrons (avec levier et pièces critiques) | ≈ 430 ms sans cache ; les écrans lisent la projection en cache (recalculée seulement si l'état change) ; Pulse ≈ 0,7 s (deux rejeux) |

## 6. Trouvé en chemin

- **Fuite de l'événement de retrait** (corrigée avant commit) : mon premier texte de recomposition disait « pas à la
  personne qui s'est retirée ». Il révélait qu'un retrait avait eu lieu ; le test d'anonymat l'a attrapé.
- **Ordre des pertes** par identifiant de membre (fuite faible) : les pertes sont maintenant ordonnées par emplacement
  du patron.
- **Même frontière hors onboarding** : les besoins, les offres et les réponses entraient aussi bruts dans le journal.
  Tous corrigés dans le même commit de sécurité.

## 7. Non fait / limites

- **Consentement de finalité, portée** : il porte sur UNE offre et UN emplacement jusqu'à la fin de la fenêtre. Il n'y
  a pas de consentement « permanent » multi-fenêtres (volontaire).
- **Plafond d'Ask** : il compte les *réponses*, pas les Asks *vues*. Lire ne doit rien écrire, donc une Ask montrée
  mais ignorée ne compte pas. Choix assumé.
- **Personnes retirées** : elles ne peuvent plus re-consentir pour cette finalité (comme un refus). Un « revenir »
  explicite n'est pas construit.
- **IA** (EXTRACT, NARRATE, NORMALIZE), parité IA ON/OFF non vacueuse, statut honnête des appels IA, QR juré avec
  expiration et limitation par code : **Phase 3**, comme convenu.
- **Artefacts** (vidéo, captures, DEMO_SCRIPT § 6, PREUVES, `competition/*`) : non régénérés (fin de Phase 3).
