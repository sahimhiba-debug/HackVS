# Matrice d'acceptation — tranche « banc d'essai partagé »

Résultats **exécutés** le 2026-09-29 dans cet environnement (voir `PREUVES.md`). « Auto-évaluation » : aucune ligne
n'est une validation indépendante. Chemins relatifs à `prototype/`. `E2E` = `tests/test_e2e_pulse.py` (vrai navigateur,
deux contextes) ; `DOM` = `tests/test_essai.py` ; `SEC` = `tests/test_essai_securite.py` ; `INÉDITS` = `tests/test_essai_cas_inedits.py`.

## A. Ce que la démonstration doit prouver
| ID | Comportement attendu | Implémentation | Preuve | Résultat | Limite |
|---|---|---|---|---|---|
| P1 | Une personne formule une intention | `ClubPulse.preparer_essai`, écran « Proposer un essai » | E2E nominal | ✅ | formulaire si pas d'Apertus |
| P2 | Une proposition compréhensible est préparée | `Intelligence.structurer_essai` + brouillon ; vue `VuesEssai.essai` (quoi, pourquoi, qui, contraintes, durée, critère, partage, manque, prochaine décision) | E2E nominal ; captures `captures/` | ✅ | secours : le membre écrit gestes et critère |
| P3 | Chacun choisit ce qu'il accepte | accord par personne, lié à SA portée et à UNE version (`essai.portee`, `_accord_donne`) ; le porteur choisit l'offre | DOM nominal ; E2E | ✅ | — |
| P4 | Une modification réelle change les conditions | `modifier_offre` → `_reevaluer` → A_ADAPTER, alternatives | DOM `test_moins_de_temps…` ; E2E (Markus 15→5 min en direct) | ✅ | perturbations gérées : durée, retrait d'offre, refus, retrait, critère |
| P5 | Ni accord ni disponibilité inventés | offres explicites seulement ; silence → EXPIRE ; modèle sans champ « accord » | DOM `test_silence…` ; SEC `test_formulation_hostile…` | ✅ | — |
| P6 | Une action peut réellement avoir lieu | lancement revérifié ; contribution **constatée** par le porteur | E2E (geste physique, constat) | ✅ | le logiciel n'observe pas le geste : déclaration humaine |
| P7 | Le résultat garde limites et désaccords | observation : qualification + portée obligatoire ; avis confirme/conteste ; révisions gardées | DOM, INÉDITS `test_observation_contestee…`, E2E (contestation visible) | ✅ | — |
| P8 | Mémoire partageable seulement avec les droits | `niveau_partage` = le plus restrictif ; défaut « participants » | DOM `test_droits…`, SEC `test_ancienne_observation…`, INÉDITS | ✅ | pas de page « mémoire du Club » publique : liste « réutilisable » seulement |

## B. Invariants obligatoires
| ID | Invariant | Où c'est garanti | Preuve | Résultat |
|---|---|---|---|---|
| I1 | Aucun lancement sans autorisation applicable AU MOMENT du lancement | `Banc.lancer` revérifie la couverture sous le verrou, écrit la réévaluation, refuse | DOM `test_moins_de_temps…` (lancer → 409) ; SEC `test_retrait_pendant_le_lancement…` | ✅ |
| I2 | Aucune disponibilité inventée | `candidats` / `offre_couvre` : offre publiée, active, couvrante, capacité | DOM, INÉDITS `test_aucune_solution…`, `test_contradiction…` | ✅ |
| I3 | Aucun accord déduit du silence | aucune transition sur délai sauf EXPIRE | DOM `test_silence…` ; INÉDITS `test_offre_expiree…` | ✅ |
| I4 | Aucun succès déduit du silence | RESULTAT_INCONNU ; CONTRIBUTION_RECUE ≠ résultat | DOM `test_silence…`, `test_parcours_nominal…` | ✅ |
| I5 | Pas de réservation au-delà de la capacité | `reservations` + contrôle à l'accord et au lancement | DOM `test_capacite_jamais_depassee` | ✅ |
| I6 | Nouvelle audience ≠ ancien accord | réutilisation = droit explicite de CHACUN ; accord d'essai ≠ diffusion | INÉDITS `test_changement_d_audience…` ; SEC | ✅ |
| I7 | Aucune mémoire plus visible qu'autorisé | vues filtrées ; console sans texte d'observation | SEC `test_observation_reservee…`, `test_secret_temoin…` | ✅ |
| I8 | Aucune transition critique décidée par le modèle | le modèle ne produit qu'un brouillon (schéma fermé) | SEC `test_formulation_hostile…` ; `tests/test_architecture.py` | ✅ |
| I9 | Aucun refus redemandé | refus et retraits exclus des candidats ; `decider` → 409 | DOM `test_un_refus…`, E2E refus | ✅ |
| I10 | Aucun résultat négatif effacé | révisions d'observation et avis en ajout seul | INÉDITS `test_observation_contestee…`, `test_contribution_inutilisable…` ; E2E (négatif gardé) | ✅ |

## C. Critères de sortie (§ 21 du mandat)
| ID | Critère | Preuve | Résultat | Limite |
|---|---|---|---|---|
| S1 | Une tranche complète fonctionne | E2E nominal (formulation → réutilisation) | ✅ | — |
| S2 | Deux acteurs, sessions distinctes | E2E : deux contextes de navigateur, deux codes | ✅ | en salle : deux téléphones (non testé ici, mêmes écrans) |
| S3 | Compréhensible sans exposer l'architecture | trois onglets ; « prochaine décision » en tête | ✅ auto-évalué | aucun test utilisateur |
| S4 | Une modification substantielle change la décision | E2E perturbation ; DOM `test_modification_cosmetique…` | ✅ | — |
| S5 | Anciens accords non réutilisés hors portée | SEC `test_accord_d_une_ancienne_version…`, `test_remplacement…` | ✅ | — |
| S6 | Refus et impossibilité gérés | E2E `test_refus_sans_alternative…` ; INÉDITS | ✅ | — |
| S7 | Contribution reçue ≠ succès | DOM, E2E (« aucun résultat n'en découle ») | ✅ | — |
| S8 | Droits de mémoire et de réutilisation distincts | DOM, SEC, INÉDITS | ✅ | — |
| S9 | Mode IA ou secours honnête | E2E (« aucun modèle utilisé ») ; SEC (panne → formulaire déclaré) | ✅ | **Apertus réel NON testé** (aucun identifiant) |
| S10 | Contrôles critiques exécutés | `make quality-check` vert (486 + 5 E2E) | ✅ | — |
| S11 | Démonstration reproductible | « Nouvelle démonstration » ; E2E rejoué en CI | ✅ | réseau de salle non testé |
| S12 | Limites documentées | `HANDOFF_FOR_CODEX.md` §16 | ✅ | — |
| S13 | Périmètre visible réduit | `web/pulse/app.html`, `console.html` | ✅ | anciennes routes API et ancien prototype toujours servis (hors parcours, protégés) |
| S14 | Dossier d'audit complet | ce dossier | ✅ auto-évalué | — |
