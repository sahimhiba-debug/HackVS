# Matrice d'acceptation — tranche « action collective »

Auto-évaluation, exécutée dans cet environnement (voir `PREUVES.md`) ; aucune ligne n'est une validation indépendante.
Chemins relatifs à `prototype/`. `AC` = `tests/test_action_collective.py` (API, sessions distinctes) · `CR` =
`tests/test_creneaux.py` (domaine) · `AU` = `tests/test_audit_essai.py` · `INV` = `tests/test_essai_invariants.py` ·
`E2E` = `tests/test_e2e_action.py` (Chromium : deux téléphones + écran commun).

## A. Ce que la démonstration doit montrer
| ID | Comportement | Preuve | Résultat | Limite |
|---|---|---|---|---|
| D1 | Besoin formulé avec ses mots → exigences proposées, origine affichée | E2E (« Règles simples »), AC `_action` | ✅ | règles, pas Apertus |
| D2 | Aucune offre seule ; proposition au recouvrement des disponibilités déclarées | CR `test_la_proposition_n_existe…`, AC recouvrement | ✅ | recherche au quart d'heure |
| D3 | Chacun accepte SA part sur SON téléphone ; rien n'est supposé pour les autres | AC parcours complet, E2E | ✅ | téléphones : deux contextes de navigateur |
| D4 | Valeur choisie par le jury → recalcul, adaptations, ou blocage honnête | AC `test_la_valeur_choisie_par_le_jury…` (6 valeurs), E2E (17:00) | ✅ | dimension principale : l'heure de la voix |
| D5 | Adaptation choisie → nouvelle version → tous reconfirment | AC parcours, E2E | ✅ | — |
| D6 | Résultat concret transmis, reçu, confirmé par la destinataire ; ≠ présentation tenue | AC, E2E (`livrable reçu`, aucun bouton « constater ») | ✅ | — |
| D7 | +30 jours : rien n'est reconduit ; silence ≠ succès | AC `test_trente_jours…`, E2E p6 | ✅ | horloge simulée |
| D8 | Écran commun : rôles, horaires, états ; consentement de la porteuse | AC `test_rien_n_est_projete…`, `test_la_projection_ne_montre…` (4 étapes), E2E | ✅ | — |

## B. Invariants
| ID | Invariant | Où | Preuve | Résultat |
|---|---|---|---|---|
| I1 | Aucun lancement sans accords couvrant la version au moment du lancement | `Banc.lancer` | AC (409 après perturbation), AU | ✅ |
| I2 | Aucune disponibilité inventée : une offre sans plage n'entre pas dans une action à créneau | `offre_couvre` | CR (offre sans horaire jamais retenue) | ✅ |
| I3 | Changement matériel d'une offre → l'accord ne couvre plus (P1) | `raisons_gestes` / `_materiel` | AU `test_p1_*` | ✅ |
| I4 | Chaque geste d'une même personne est vérifié (P2) | `raisons_gestes` | AU `test_p2_*` | ✅ |
| I5 | Un accord n'est gardé que si sa portée est inchangée | `portee` / `_accord_donne` | AC (Pauline « ancienne » après changement de lieu), INV | ✅ |
| I6 | Jamais sous la durée minimale fixée par la porteuse | `solutions` | CR, AC (variante 30 min = minimum) | ✅ |
| I7 | Refus, retrait, silence, expiration ont un effet réel | `decider`, `retirer`, `echeances` | CR, INV, AC (retrait après réception) | ✅ |
| I8 | Double clic, décisions concurrentes, version périmée : sans contournement | `_verifier_version`, idempotence | AC (409 version−1, double réception 409), INV | ✅ |
| I9 | `IMPOSSIBLE` non terminal : un fait nouveau rouvre une adaptation, jamais un lancement | `_reevaluer` | AC `test_sans_solution…` | ✅ |
| I10 | Une personne n'est jamais engagée sur deux créneaux qui se chevauchent | `occupations` | CR `test_une_personne_n_est_jamais…` | ✅ |
| I11 | Un état n'est jamais affiché plus fort que sa preuve | `VuesEssai.palier` | AC, E2E | ✅ |
| I12 | La console ne décide jamais à la place d'un membre qui a son téléphone | `JOUABLES` | AC `test_personne_ne_decide…` (403) | ✅ |
| I13 | Aucune transition critique décidée par un modèle | schéma fermé, `test_architecture.py` | `test_frontiere_ia.py` | ✅ |

## C. Critères de sortie
| Critère | Résultat | Réserve |
|---|---|---|
| Tranche intégrée démontrable (téléphones + écran commun + console) | ✅ | réseau de salle et vrais téléphones non testés |
| Constats P1/P2 corrigés, tests de régression prouvés | ✅ | — |
| Perturbation réelle + adaptation correcte + blocage honnête | ✅ | — |
| Enregistrement réel, identifié par son commit | ✅ | ne prouve pas une réaction en direct à un choix nouveau |
| WOW audit et attaque du jury, corrections rejouées | ✅ auto-évalué | aucun juré réel (`REVUE_JURY.md`) |
| IA : tâche utile, validée, repli visible, trace | ✅ | **Apertus réel NON exécuté** |
| Dossier à jour (scénario, lancement, scripts, storyboard, secours, limites, points d'audit) | ✅ | temps de parole estimés, non chronométrés par un humain |
