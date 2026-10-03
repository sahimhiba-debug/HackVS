# Preuves de validation — tranche « action collective » (2026-09-30)

Environnement de développement (Linux x86-64, Python 3.11, Chromium headless). Commandes réellement exécutées ;
codes de sortie lus. Aucun secret, aucune donnée personnelle réelle. Dernier enregistrement vidéo : commit `a03bfa6` (Phase 3 ; chiffres courants : `docs/audit/PHASE_3.md`).

## Commandes et résultats
| Commande (depuis la racine sauf mention) | Résultat |
|---|---|
| `make quality-check` | code 0 — secrets : aucun ; ruff : OK ; mypy : 73 fichiers sans erreur ; pytest : **514 réussis** (dont le parcours navigateur `test_e2e_action.py`) ; bout en bout historiques : **5 réussis** ; évaluations 20/20 ; registre des affirmations OK |
| `cd prototype && python -m pytest -q tests/test_action_collective.py` | 18 réussis : parcours par l'API (sessions distinctes), personne ne décide pour un autre, blocage puis réouverture, projection sans nom (4 étapes), perturbation jouée, recouvrement réel, +30 jours, fiche ≠ présentation, consentement de projection, **6 heures choisies par le jury** |
| `cd prototype && python -m pytest -q tests/test_creneaux.py tests/test_audit_essai.py` | réussis (créneaux, livrable/présence, double réservation ; P1/P2) |
| `cd prototype && HACKVS_CAPTURES=… python -m pytest -q tests/test_e2e_action.py` | 1 réussi — deux téléphones (390×844, 412×915) + écran commun 1920×1080 ; captures `captures/action/p0…p6, a1…a4, b1` |
| `python scripts/enregistrer_demo.py --commit a03bfa6` (serveur démo, port 8767) | vidéo **87 s** (précédente : 89 s au commit `dd75a7c`), 1920×1080, exécution continue sans montage ; étapes horodatées `captures/action/demo_action.json` |
| `cd prototype && python -m eval.eval_apertus` | Apertus **NON EXÉCUTÉ** ; repli `comprendre_action` : **4/6** en notation exacte (échecs listés dans `eval/resultats_apertus.md`) |
| `env \| grep -c '^APERTUS_'` | 0 — aucun appel réel possible ; rien créé, rien payé |

## Tests de régression prouvés (échouent sans la correction)
| Correction | Vérification |
|---|---|
| P1, P2 (commit `267c9c9`) | 4 des 5 tests de `test_audit_essai.py` échouaient sur l'ancien code (vérifié en retirant la correction) |
| Couverture figée après l'action | règle désactivée → `test_trente_jours…` échoue ; restaurée |
| Double réservation | règle désactivée → `test_une_personne_n_est_jamais_engagee…` échoue ; restaurée |
| Retrait après l'action | garde désactivée → `test_trente_jours…` échoue ; restaurée |
| Fiche ≠ présentation, projection consentie, recouvrement | le test appelle un comportement ou un champ absent de l'ancien code (échec direct) |

## Délais mesurés (geste sur un téléphone → visible sur l'écran commun)
L'écran commun relit le serveur toutes les 0,7 s : le délai attendu est 0–0,7 s plus la requête.
| Mesure | Contexte | Valeurs observées (exécutions successives de ce jour) |
|---|---|---|
| accord → écran commun | test navigateur, page de projection seule | 229, 278, 627, 704 ms ; 678 ms (réenregistrement Phase 3, `delais.json`) |
| perturbation → écran commun | test navigateur | 324 à 394 ms |
| perturbation → écran commun | enregistrement (régie à 3 cadres + capture vidéo) | 929 à 944 ms |
Machine de développement, en local : **pas** un réseau de salle.

### Ajouts du 01.10 (IA réelle — n'annulent rien de ce qui précède, daté)
| Commande | Résultat |
|---|---|
| `make sonde-ia` (APERTUS_MODEL=swiss-ai/Apertus-v1.5-70B, API CSCS) | modèles, JSON simple, `json_schema` strict, tools, non-thinking : **SUPPORTED** (`3c2ff23`, `docs/audit/probe_publicai.md`) |
| `make banc-ia` (26 cas fictifs, chemin du produit) | modèle accepté et juste **1/26** ; rejetées 25 ; vu par le membre juste 17/26 (règles seules 16/26) — `prototype/eval/resultats_comprendre_action.md` |
| `make latence-ia N=30` | tâche du produit : médiane 5329.2 ms, p95 6021.2 ms, n = 30, 0 erreur ; requête courte : médiane 425.9 ms, p95 458.4 ms — `docs/audit/latence_apertus.md` |
| `make test` · `make e2e` | 1301 réussis · 22/22 (dont `test_e2e_ia.py`, faux Apertus HTTP local) |

## Gel du 02.10.2026, 18:00 (CEST) — chiffres définitifs

Mesuré sur le commit `5b386d5` (HEAD de `claude/modest-bohr-xvk53n`, identique à `origin`, aucun changement local) ;
le tag annoté `gel-demo` est posé sur le commit qui ajoute cette section (docs seulement), après sa CI verte.

| Chiffre | Valeur | Source |
|---|---|---|
| Tests (suite hors E2E, `make test`) | **1 359 réussis**, 0 échec | exécution locale sur `5b386d5`, 02.10 15:34 UTC (6 min 32 s) |
| Parcours de bout en bout dans Chromium (`make e2e`) | **22/22 réussis** | exécution locale sur `5b386d5`, 02.10 15:41 UTC ; mode salle (réseau local seul, IA OFF) vert en CI, job `salle` du run #178 |
| CI sur `5b386d5` | **verte** | run CI [#178](https://github.com/sahimhiba-debug/HackVS/actions/runs/36958464092) (qualité, salle, dépendances, reproductibilité) |
| Mutation du cœur du registre (`intelligence/capacites.py`) | **1 229 tués / 1 327**, 98 survivants **tous classés équivalents**, 0 sans test, 0 non vérifié, 0 suspect | run Mutation [#16](https://github.com/sahimhiba-debug/HackVS/actions/runs/36984623513) sur `5b386d5`, 02.10, porte durcie (échec si un survivant n'est pas classé) |
| Geste sur un téléphone → écran commun | **moins d'une seconde** (229–704 ms en test navigateur ; 929–944 ms en enregistrement à 3 cadres) | « Délais mesurés » ci-dessus ; machine de développement, pas un réseau de salle |
| Écriture sans geste | **0** (aucune route de lecture n'écrit) | CLAIMS n° 28, test associé |
| Modèle (Apertus, tâche du produit) | médiane **5,3 s**, p95 6,0 s, n = 30, 0 erreur — **mesure du 01.10, non refaite au gel** | `make latence-ia N=30` → `docs/audit/latence_apertus.md` ; CLAIMS n° 40 ; depuis l'environnement de développement, pas depuis la salle |
| Qualité du modèle sur la tâche | **1/26** accepté et juste | CLAIMS n° 39, mesure du 01.10 |

**Hors gel, hors deck (règle FINAL_AUDIT § 10).** Mutation de `essai.py` (F37, campagne locale, population d'avant
H2) : 2 311 tués / 3 528, 1 150 survivants **non classés**, 67 sans test — consignée dans VAGUES_CORRECTIONS § 4.1,
pas un chiffre de présentation.

Après le gel : uniquement `docs/` ou correctif bloquant de démo validé par Hiba.

## Foire 2026 — mesures de la nuit du 03 au 04.10 (branche `foire-2026`)

Chiffres MESURÉS seulement ; le reste est dans `docs/RAPPORT_NUIT.md`.

| Mesure | Résultat | Commande |
|---|---|---|
| Classification des 26 cas existants dans la taxonomie des métiers, par Apertus (`swiss-ai/Apertus-v1.5-70B`, API CSCS), 03.10 13:10 UTC | 25 / 26 sorties acceptées par la validation du code, dont 8 abstentions ; 1 rejetée (métier hors taxonomie). **Aucune exactitude mesurée** (pas encore d'étiquettes humaines) | `make eval-classification FOURNISSEUR=apertus` → `prototype/eval/resultats_classification/cas-26-apertus.md` |
| **Extraction `comprendre_action`, 26 cas, rejeu du 03.10** (14:01–14:03 UTC, commit `a0d1e46`) — modèle exact `swiss-ai/Apertus-v1.5-70B`, point d'accès `https://api.inference.cscs.ch/v1` — **Apertus 1.5 servi par le CSCS (Lugano)**, pas par Public AI, prompt `comprendre_action_v1`, même harnais, même jugement | **1/26 modèle juste** (inchangé) ; 26/26 JSON lisible et conforme au schéma ; 25 rejetées par la validation ; produit juste 17/26 ; règles seules 16/26 ; latence médiane 5,7 s, p95 7,4 s. **Pas de progression** : le « 1/26 » du 01.10 était **déjà** mesuré sur ce même modèle Apertus 1.5 70B (`eval/resultats_comprendre_action.md`, 01.10 19:45 UTC) — les deux mesures sont gardées | `make banc-ia FOURNISSEUR=apertus` → `prototype/eval/resultats_banc/apertus.md` (+ `.json`, sorties brutes) |
| Langue détectée sur les 26 cas | 22 fr, 2 de (dont suisse allemand), 1 it, 1 en — conforme aux textes | `test_foire_tally.py::test_langues_des_26_cas_detectees_justes` |
| Phrases Tally (QR de la Foire, instantané du 03.10, 21 réponses) | 21 gardées (0 doublon, 0 contact, 0 vide) ; langue réelle détectée : 20 fr, 1 en (passée par la page française) — phrases hors dépôt | `make ingest-tally` (CSV en `docs/data/tally_phrases.csv`, ignoré par git) |
| Classification des 21 phrases Tally par Apertus (`swiss-ai/Apertus-v1.5-70B`), 03.10 13:47 UTC — **Apertus seulement** (consentement) | 21 / 21 sorties acceptées par la validation, **dont 20 abstentions** ; 1 métier proposé. **Aucune exactitude mesurée** : feuille d'annotation (`metier_attendu`, `domaine`) à remplir par l'équipe | `make eval-classification FOURNISSEUR=apertus` → `prototype/eval/resultats_classification/foire-2026-qr-apertus.md` |

## « La carte devient le profil » — Apertus 1.5 (vision), 6 cartes FICTIVES (03.10)

Modèle exact `swiss-ai/Apertus-v1.5-70B`, API CSCS ; attentes fixées avant l'exécution (`prototype/eval/cas_carte.json`) ;
chemin du produit (`carte.proposer`) ; rejeu : `cd prototype && python -m eval.banc_carte` → `eval/resultats_carte/apertus.md`.
**6 cartes, une seule mise en page : ne démontre pas une qualité générale.**

| Version du chemin | entreprise | métier | zone | langue | latence médiane |
|---|---|---|---|---|---|
| 1. un seul appel (image → champs), 14:22 UTC | 0/6 | 1/6 | 1/6 | 6/6 | ~1,0 s |
| 2. deux temps (image → texte recopié, puis texte → champs sous schéma), 14:31 UTC — **retenue** | 4/6 | 5/6 | 5/6 | 6/6 | ~1,8 s |

Constat : en un seul appel, le modèle mettait le nom de la PERSONNE dans « entreprise » et répondait presque toujours
« communication » / « Vaud » ; il recopie pourtant le texte de la carte sans faute. Le membre confirme ou corrige
toujours ; la photo n'est jamais conservée.

## Mode salle — charge de 80 téléphones simulés (03.10, **serveur local**)

Mesure contre un **serveur local** (uvicorn, un processus, la machine de développement de la session cloud ; pas à
travers Internet, pas sur le VPS). Rejeu : `cd prototype && python scripts/charge_salle.py --local --n 80` ; contre le
serveur déployé : `python scripts/charge_salle.py --url https://<domaine> --jeton <HACKVS_CONSOLE_JETON> --n 80`.

| Mesure | Résultat |
|---|---|
| Téléphones simulés (scan, capacité + consentement, relecture, réponse, un retrait) | 80, en parallèle ; 329 requêtes en 0,67 s |
| Erreurs | **0** |
| p50 / p95 par route (ms) | entrer 178,9 / 200,7 · déclarer 159,9 / 208,4 · relire (moi) 115,9 / 138,9 · répondre 66,5 / 79,2 · écran 6,8 / 19,2 |
| Cohérence finale | écran = téléphones (80 participants, capacités par métier, réponses par choix ; « < 3 » accepté seulement si le vrai nombre est 1 ou 2) ; anneau fermé ; **purge vérifiée** (0 participant après) |

## Non exécuté (et pourquoi)
- Apertus réel : aucun identifiant fourni. *(vrai au 30.09 ; depuis le 01.10, voir « Ajouts du 01.10 » ci-dessus.)*
- Vrais téléphones sur le réseau d'une salle : remplacés par des contextes de navigateur indépendants.
- Jury, membres, exposants réels : aucun contact (interdit par le mandat) ; aucune mesure d'usage.
- Chronométrage humain des scripts : temps de parole **estimés** (150 mots/min).
