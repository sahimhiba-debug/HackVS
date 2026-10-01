# Registre des affirmations (claims) — 01.10.2026

Chaque affirmation publique du dépôt (README, script de démo, écrans, design system, documents d'audit) est classée :

- **A — prouvée automatiquement** : un test reproductible échoue si elle devient fausse (le test est nommé).
- **B — mesurée** : une mesure reproductible existe (commande nommée), sans garantie absolue.
- **C — démontrable à la main** : on peut la montrer pendant le pitch ; aucun test ne la garde.
- **D — non prouvée** : elle est retirée ou reformulée ; jamais présentée comme une garantie.

Chemins de test relatifs à `prototype/tests/`. Le dossier `/competition/` (pitch de l'ancien produit) n'est PAS dans ce
registre : il est en quarantaine, et rien n'y doit être présenté.

## README

| # | Affirmation | Classe | Preuve |
|---|---|---|---|
| 1 | « Aucune capacité, aucun consentement, aucun destinataire n'est jamais choisi par un modèle » | A | `test_frontiere_ia.py`, `test_provenance_ia.py`, `test_parite_ia.py` (parité ON/OFF de l'état métier), `test_demande_confirmee.py` (F01 : interpréter n'écrit rien) |
| 2 | Une capacité n'existe que si chaque pièce est déclarée, valable à la date, consentie pour cette finalité | A | `test_capacites_regles.py`, `test_capacites_oracle.py` (oracle en force brute), `test_banc_finalite.py` |
| 3 | Pièce disparue → DÉGRADÉE, cause dite par le rôle, jamais la personne | A | `test_capacites_retrait.py`, `test_capacites_offre_ne_couvre_plus.py` |
| 4 | « une recomposition est calculée, jamais appliquée » | A | `test_recomposition_jamais_appliquee.py` (ajouté le 01.10 : le claim n'était qu'implicite) |
| 5 | Journal rejouable : un `kill -9` puis `make demo` rend le même monde, les sessions, le passe juré, le rejeu IA sans modèle | A | `test_redemarrage_kill9.py` (vrai uvicorn, SIGKILL, modèle mort à la relance) |
| 6 | L'ancien prototype répond 404 sauf `HACKVS_ANCIEN_PROTOTYPE=1`, et alors à cette machine seulement | A | `test_service_ancien.py` |
| 7 | Parité IA ON/OFF | A | `test_parite_ia.py` (non vacueuse : `test_la_parite_vacueuse_est_detectee`) |
| 8 | « Apertus n'a jamais été appelé depuis cet environnement » ; qualité d'un vrai modèle NON DÉMONTRÉE | C (vrai, et dit) | aucune clé configurée ; `docs/audit/probe_publicai.md` |
| 9 | « ~1 250 tests et 17 E2E hermétiques (aussi en mode salle) » | A pour 17 E2E (`test_readme.py::test_les_chiffres_du_readme_sont_ceux_du_depot`) ; B pour le total (compté au dernier `make test`) | CI : jobs `salle` et `reproductibilite` |
| 10 | Mutation `capacites.py` : 1 229 / 1 327 tués, 98 survivants tous classés | B (campagne locale du 01.10) | `docs/audit/mutants_survivants.txt` ; la campagne GitHub (#12) ne l'a pas encore confirmé — voir FINAL_AUDIT § 10 |
| 11 | Console : exige un jeton hors de la machine locale | A | `test_securite_pulse.py::test_console_sans_jeton_ne_repond_qu_a_cette_machine`, `test_autorisation_balayage.py` |

## Script de démonstration (`docs/audit/club-pulse-pivot/DEMO_SCRIPT.md`)

| # | Affirmation | Classe | Preuve |
|---|---|---|---|
| 12 | Le jury change une condition ; le système dit ce qui tombe, ce qui tient, ce qui reste possible — ou BLOQUÉ | A | `test_action_collective.py::test_la_valeur_choisie_par_le_jury_n_est_pas_fixee_d_avance` (6 valeurs) |
| 13 | « personne ne décide à la place d'un autre » (la console ne peut pas jouer Léa) | A | `test_action_collective.py`, `test_boucle.py` |
| 14 | « accord → écran commun : 678 ms » ; à l'oral « moins d'une seconde » | B | `delais.json` (réenregistrement Phase 3) ; valeurs observées 229–704 ms (`PREUVES.md`). L'écran relit toutes les 0,7 s : « moins d'une seconde » est l'ordre de grandeur mesuré, pas une garantie |
| 15 | Tout tourne sans Internet (« mode salle ») | A | `make e2e-salle` / job CI `salle` : espace réseau vide, extérieur injoignable vérifié, IA OFF |
| 16 | Vrais téléphones sur le point d'accès du portable | C + A partiel | config : `test_demo_salle_telephones.py` (écoute réseau, QR à l'URL publique, console refusée aux téléphones) ; parcours vérifié dans Chromium par une adresse réseau (R-01). **Jamais testé sur de vrais téléphones ni un vrai Wi-Fi** : rituel § 9.5 étape 6 |
| 17 | QR juré : 15 min, usage unique, attribué au jury | A | `test_qr_jure.py`, E2E `test_qr_jure_etabli_telephone_usage_unique` |
| 18 | « Le serveur plante → le monde revient tel quel » | A | = n° 5, et `test_redemarrage_kill9.py::test_reinitialisation_puis_kill_9…` (R2) |
| 19 | Retrait anonyme : « un composant n'est plus disponible », jamais le nom ni la raison | A | `test_capacites_retrait.py` (noms et « retir » absents de tout écran commun et des demandes des autres) |

## Écrans (textes visibles)

| # | Affirmation | Classe | Preuve |
|---|---|---|---|
| 20 | Écran commun : « des rôles, jamais des noms » | A | `test_action_collective.py::test_la_projection_ne_montre_ni_nom_ni_secret` |
| 21 | « Formulaire : aucun modèle utilisé » / « IA : aucun modèle configuré — forme déterministe » | A | E2E `test_e2e_pulse.py` (libellé), `test_appels_ia_statuts.py` (MODEL_CALLED / CACHE_REPLAY / FALLBACK_FORM véridiques) |
| 22 | « Votre passe est journalisé : ce que vous faites est attribué au jury » | A | `test_qr_jure.py` (fait `PASSE_JURE`) |
| 23 | « Tout effacer » : « le journal garde une trace technique sans nom ni contact » | A | `test_effacement.py` (nom et courriel absents des vues après effacement, rejoué au redémarrage) ; E2E `test_tout_effacer_annonce_ce_qui_reste_avant_le_geste` (annoncé AVANT le geste) |
| 24 | « hors ligne : écran figé » (le téléphone dit qu'il est hors ligne au lieu de montrer du périmé) | A | E2E `test_e2e_pulse.py::test_application_face_aux_pannes_reseau` |
| 25 | Contenu hostile affiché comme du texte | A | E2E `test_contenu_hostile_affiche_comme_du_texte` ; aucun `innerHTML` dans `web/pulse/` (constructeur DOM) |
| 26 | « Au plus 1 demande par membre et par semaine » (planche Téléphone) | A | `test_capacites_regles.py` (plafond `HACKVS_PLAFOND_JOURS`, sélection d'Ask, P2.5) |

## Design system et planches (`docs/design/DESIGN_SYSTEM.md`)

| # | Affirmation | Classe | Décision |
|---|---|---|---|
| 27 | « chaîne HMAC vérifiée ✓ » (planche Passeport) | **D** | **FAUX** : le journal n'a pas de chaîne HMAC (identifiants de faits par empreinte de contenu, sans chaînage). Clôturé dans DESIGN_SYSTEM § 8 : jamais affiché |
| 28 | « 0 capté passivement » (couverture, planche Mes données) | **D** | aucun compteur dans le produit. Clôturé § 8 ; **couverture du pitch : décision de Hiba** |
| 29 | « Répondre à une demande : 10 secondes, sans compte, sans nom » (couverture) | **D** | « 10 secondes » non mesuré ; « sans compte » FAUX (répondre exige un compte activé par code ; seul le passe juré est sans compte). **Couverture du pitch : décision de Hiba** (retirer, ou chronométrer au rituel) |
| 30 | « 1 198 événements », « MODEL_CALLED · 678 ms » (planche Passeport) | **D** | contenus d'illustration ; clôturés § 8 |
| 31 | § 6 « contrastes validés » | **D → corrigé** | mesuré : trois couleurs des planches échouaient WCAG AA ; le produit s'en écarte (§ 8) et le test navigateur `test_lisible_et_touchable_au_telephone_et_sur_les_ecrans` garde contraste et cibles ≥ 44 px |
| 32 | Polices auto-hébergées, aucune requête externe | A | E2E hermétiques (`test_e2e_hermetique.py` : toute requête externe échoue le test) |

## Documents d'audit

| # | Affirmation | Classe | Note |
|---|---|---|---|
| 33 | Chaque correction F01–F40, R-01–R-07, H1–H5 : test rouge d'abord, contre-épreuve | A | chaque commit nomme son test ; `VAGUES_CORRECTIONS.md`, `REVUE_PUBLIQUE.md`, `FINAL_AUDIT.md` |
| 34 | `REVUE_PUBLIQUE.md` : « Démarrage 4 s », « 0,9 s à froid puis 5 ms » | B (une seule mesure, avant H2) | remplacé par `make perf` (n itérations, p95) : FINAL_AUDIT § 8 |
| 35 | `PREUVES.md` : « 514 réussis » (30.09) | B daté | exact à sa date ; chiffres finaux figés au gel |
| 36 | Mutation de `essai.py` (F37) | B (en cours) | chiffres bruts, survivants NON classés ; mesurés sur `essai.py` d'AVANT les correctifs H2 (copie figée) — dit dans FINAL_AUDIT § 10 |
| 37 | « Aucun CRITICAL » | C | constat d'audit, pas une preuve d'absence |

## Ce qui reste à décider par Hiba (claims du pitch)

- n° 28 et 29 : la couverture du deck porte deux affirmations non prouvées (« 0 capté passivement », « 10 secondes, sans
  compte »). Rien n'a été modifié dans le pitch (consigne : demander avant de toucher un claim important du pitch).
