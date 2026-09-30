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

## Non exécuté (et pourquoi)
- Apertus réel : aucun identifiant fourni.
- Vrais téléphones sur le réseau d'une salle : remplacés par des contextes de navigateur indépendants.
- Jury, membres, exposants réels : aucun contact (interdit par le mandat) ; aucune mesure d'usage.
- Chronométrage humain des scripts : temps de parole **estimés** (150 mots/min).
