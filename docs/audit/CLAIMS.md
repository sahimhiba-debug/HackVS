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
| 8 | « Apertus (`swiss-ai/Apertus-v1.5-70B`, API d'inférence CSCS) répond depuis cet environnement : JSON, schéma strict, tools — sonde du 01.10 ; qualité sur les tâches du Club NON DÉMONTRÉE ; la démo tourne sans modèle (forme déterministe) » | B | `make sonde-ia` → `docs/audit/probe_publicai.md` (`3c2ff23`) ; latence : `make latence-ia` → `docs/audit/latence_apertus.md`. Ancienne formulation (« Apertus n'a jamais été appelé ») devenue fausse le 01.10 ; avant : clé refusée pour `Apertus-70B-Instruct-2509` (403, `31d10e5`) |
| 9 | « ~1 430 tests et 26 E2E hermétiques (aussi en mode salle) » | A pour 26 E2E (`test_readme.py::test_les_chiffres_du_readme_sont_ceux_du_depot`) ; B pour le total (compté au dernier `make test` : 1 434 le 03.10, branche foire-2026) | CI : jobs `salle` et `reproductibilite` |
| 10 | Mutation `capacites.py` : 1 229 / 1 327 tués, 98 survivants tous classés | B (mesure reproductible, confirmée en CI) | campagne GitHub #15 avec la porte durcie (`4233cef`) : population 1 327, tués 1 229, survivants 98, sans test 0, non vérifiés 0, suspects 0, non classés 0 ; `docs/audit/mutants_survivants.txt` |
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
| 28 | ~~« 0 capté passivement »~~ → **« Lire ne capte rien : aucune écriture sans geste »** (couverture ; décision D1) | **A** | `test_autorisation_balayage.py::test_lire_ne_capte_rien_aucune_route_de_lecture_n_ecrit_au_journal` (CHAQUE route GET servie appelée, lignes du journal SQLite comptées avant / après) et `test_recomposition_jamais_appliquee.py`. L'ancienne formulation était D (aucun compteur) |
| 29 | ~~« Répondre à une demande : 10 secondes, sans compte, sans nom »~~ → **« Répondre : trois boutons »** + **« Retrait toujours anonyme »** ; « sans compte » réservé au **« passe juré 15 min, sans compte »** (décision D1) | **A** | trois boutons : E2E `test_etabli_telephones_reponse_recu_retrait_anonyme` (Oui / Non / Pas cette fois) ; retrait anonyme : `test_capacites_retrait.py` ; passe juré : `test_qr_jure.py`. **La durée** (« N secondes ») : **non affichée** tant qu'elle n'est pas chronométrée au rituel § 9.5 (3 mesures, la PIRE affichée) — classe B ensuite. « Sans compte » pour répondre à une demande : FAUX, retiré |
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

## Couverture du pitch (décision D1 de Hiba, 01.10)

- n° 28 et 29 reformulés comme ci-dessus, chacun adossé à un test. **La planche « Cover » de l'artefact Design n'a PAS
  encore été modifiée** : la modification d'un artefact partagé a été refusée par les permissions de cette session.
  Textes exacts à reporter (deux remplacements, rien d'autre) : badge 1 « 0 capté passivement » → « Lire ne capte rien :
  aucune écriture sans geste » ; ligne de pied « Répondre à une demande : 10 secondes, sans compte, sans nom » →
  « Répondre : trois boutons · passe juré 15 min, sans compte » (« Retrait toujours anonyme » est déjà le badge 2).
- Même claim « Capté passivement 0 » sur les planches Main (tuile KPI) et Phone-Retrait (« tout vient de vous ») :
  maquettes du produit, pas la couverture ; à aligner sur la même formulation lors du § 7.3 du design system.

## IA dans le parcours (mesures du 01.10, Apertus-v1.5-70B, API CSCS)

| # | Affirmation | Classe | Preuve |
|---|---|---|---|
| 38 | « Comprendre ma demande » (Agir à plusieurs) appelle réellement le modèle configuré ; sa sortie est validée (schéma, vocabulaire, catalogue, bornes, aucune donnée personnelle) ; sinon repli déterministe dit à l'écran ; le parcours continue toujours ; le serveur ne gèle pas pendant l'appel ; attente bornée | A | `test_ia_preparer_action.py` (sortie valide, JSON invalide, hors schéma, incohérente, délai, 503/401/réseau, budget, pas de gel) ; E2E `test_e2e_ia.py` (vrai navigateur, vrai serveur, faux Apertus HTTP local) |
| 39 | Qualité d'Apertus sur cette tâche : sortie **acceptée et juste dans 1/26 cas** ; 25 sorties rejetées par la validation (durées hors bornes, capacités hors catalogue, jours non ISO) ; ce que voit le membre est juste dans 17/26 cas, contre 16/26 pour les règles seules | B | `make banc-ia` → `prototype/eval/resultats_comprendre_action.md` (26 cas fictifs, attentes fixées avant exécution, SHA-256 `34bfcc37bf2f…`) ; **ne démontre pas une qualité générale** ; prompt `comprendre_action_v1` inchangé |
| 40 | Latence d'une complétion de la tâche du produit : médiane **5.3 s**, p95 **6.0 s** (n = 30, séquentiel, 0 erreur) ; requête courte : médiane 425.9 ms | B | `make latence-ia` → `docs/audit/latence_apertus.md` (01.10, depuis l'environnement de développement, via son proxy sortant ; pas depuis Cloud Run ni la salle) |

Conséquence, dite telle quelle : avec le prompt actuel, Apertus n'améliore la tâche que marginalement (+1 cas) ; la
validation et le repli empêchent qu'une sortie inventive atteigne le membre. La démonstration de scène reste sans modèle.


## Foire 2026 (nuit du 03 au 04.10, branche `foire-2026`, interrupteur `HACKVS_FOIRE`, allumé par défaut)

Toutes les nouveautés ci-dessous sont derrière `HACKVS_FOIRE` (éteint : le produit d'hier, à l'identique — la suite
entière tourne éteinte, le job CI `salle` et `make e2e` allumés). Les chiffres montrés viennent du **monde de
démonstration** (150 profils fictifs, horloge simulée), étiqueté ainsi sur chaque écran qui en affiche.

| # | Affirmation | Classe | Preuve |
|---|---|---|---|
| 41 | Rôle porté par moins de 3 membres (k = 3, `HACKVS_K_ANONYMAT`) : l'avis de retrait dit « un composant n'est plus disponible », sans le rôle ; l'écran dit qu'un rôle a été masqué, jamais lequel | A | `test_foire_anonymat.py`, E2E `test_e2e_capacites.py` (allumé : rôle absent ; éteint : comportement d'hier) |
| 42 | Message du téléphone après retrait : « Consentement retiré. Personne ne sera prévenu que c'est vous. » — **le système ne nomme jamais et ne demande jamais pourquoi ; dans un petit club on peut parfois deviner** | A (le texte) ; la limite est dite, pas prouvable | `test_foire_anonymat.py::test_message_de_retrait_ne_promet_pas_l_impossible` |
| 43 | Suivi : agrégats seulement ; tout décompte de personnes sous 3 s'affiche « < 3 » ; les décomptes de demandes (une pièce, un métier) sont dits tels quels | A | `test_foire_suivi.py` (`test_un_seul_oui_s_affiche_moins_de_trois`, `test_trois_oui_sont_dits…`) |
| 44 | Aucune donnée personnelle dans la charge utile de Suivi (ni nom, ni identifiant, ni texte d'offre, ni note) | A | `test_foire_suivi.py::test_canari_aucune_donnee_personnelle_dans_la_charge_utile` |
| 45 | Une ligne nominative n'apparaît que si les DEUX parties ont activé « visible par le Club » ; elle disparaît si l'une retire ; un membre ne peut rendre visible que son propre reçu | A | `test_foire_suivi.py::test_ligne_nominative_seulement_sous_double_accord`, `::test_un_membre_ne_rend_pas_visible…` |
| 46 | « Non » et « Pas cette fois » ont le même effet ; seul le décompte de Suivi les distingue | A | `test_foire_suivi.py::test_pas_cette_fois_est_compte_a_part…` ; effet identique : `capacites.repondre` inchangé |
| 47 | Clôture d'un reçu : résultat ∈ {signé, test sans suite, contact établi, abandonné}, note ≤ 140 caractères, journalisée ; machine à états explicite demande → accord → essai → résultat (retiré hors chemin), toute autre transition refusée | A | `test_foire_suivi.py::test_machine_a_etats_explicite`, `::test_cloture_refusee_deux_fois_retire_inconnu_resultat_note` |
| 48 | Délai médian avant le premier oui : en jours de l'horloge du monde (simulée en démonstration), non affiché sous 3 oui | A (règle) ; la valeur est celle du monde fictif | `test_foire_suivi.py` |
| 49 | Passe découverte : signé, à usage unique à l'émission (rescanné : refusé), 90 jours de l'horloge du monde (`HACKVS_DECOUVERTE_JOURS`), 3 demandes au plus, révocable (la session meurt aussitôt), limité en débit par code (jamais par adresse IP), relu du journal après redémarrage | A | `test_foire_decouverte.py`, balayage `test_autorisation_balayage.py::test_chaque_route_invite_refuse_toute_session_non_valide` |
| 50 | Le nom d'entreprise déclaré par un invité n'apparaît sur aucun écran du Club (Suivi, console des passes, Établi) | A | `test_foire_decouverte.py::test_parcours_du_jure_exposant_invite_d_annecy`, E2E `test_e2e_foire.py` |
| 51 | Une proposition d'invité ne remplit jamais une capacité (un invité n'est pas membre) | A | `test_foire_decouverte.py::test_une_proposition_d_invite_ne_remplit_jamais_une_capacite` |
| 52 | « Rejoindre le Club » écrit une INTENTION, rien de plus ; la page « prévu ensuite » : **la prise de contact par la commission est simulée en démonstration (aucun e-mail n'est envoyé)** ; Suivi compte des « intentions d'adhésion », jamais des « conversions » | A (texte et décompte) ; **la conversion d'adhésion est simulée en démonstration** | `test_foire_decouverte.py::test_intention_et_statistiques_k3`, `::test_parcours_du_jure…` (« conversion » absent) |
| 53 | Le scénario du juré « exposant invité d'Annecy » se joue dans un vrai navigateur (QR du stand → déclaration → reçu → aide → intention → passe rescanné refusé ; DE disponible) | A | E2E `test_e2e_foire.py::test_le_jure_devient_exposant_invite_d_annecy` (aussi en mode salle) |
| 54 | « Le Club cherche » : les demandes sans réponse, par métier, avec leur nombre et leur âge (jours de l’horloge du monde) ; une demande répondue quitte la liste ; une proposition d’invité la marque « à confirmer par le Club », sans dire qui | A | `test_foire_club_cherche.py` |
| 55 | « Inviter un contact » émet un passe découverte LIÉ à la demande (lien, QR, texte FR et DE) ; **le système n'envoie aucun message** (la personne transmet elle-même) | A | `test_foire_club_cherche.py::test_inviter_un_contact…`, E2E `test_e2e_foire.py` |
| 56 | Liste d'entreprises (`docs/data/entreprises.csv`, facultative) : seule la colonne métier est lue ; des DÉCOMPTES par métier (présents / absents), jamais un nom ; sans le fichier, l'écran le dit | A | `test_foire_club_cherche.py::test_liste_d_entreprises_decomptes_seulement_jamais_de_nom`, `::test_liste_sans_colonne_metier_le_dit` |
| 57 | Membre à distance : zone (Valais romand, Haut-Valais, Vaud, Genève, Haute-Savoie, Ain, autre) et langue (fr / de) déclarées sur le téléphone ; Suivi compte les membres hors Valais (k = 3), « zone non renseignée » sinon | A | `test_foire_distance.py::test_zone_et_langue_declarees_puis_suivi_hors_valais`, E2E `test_e2e_foire.py::test_membre_a_distance…` |
| 58 | Réponse depuis l'e-mail : trois liens (Oui / Non / Pas cette fois) signés, à usage unique (réponse et marque d'usage dans la même transaction), expirant avec la demande ; un lien détourné (autre choix, autre membre, échéance repoussée, signature fausse) est refusé ; « oui » exige les minimums de la pièce | A | `test_foire_distance.py` (6 tests), balayage `test_autorisation_balayage.py` (routes publiques nommées) |
| 59 | **Envoi d'e-mails : simulé en démonstration.** Aucun serveur de messagerie ; la « boîte de sortie » de la console montre les e-mails qui partiraient (dans la langue du membre), calculée à la lecture, rien n'est écrit | A (le non-envoi et la non-écriture) | `test_foire_distance.py::test_boite_de_sortie_simulee…`, `::test_la_boite_et_les_liens_n_ecrivent_rien_en_lisant` |
| 60 | « Visible par le Club » depuis le téléphone : la ligne nominative de Suivi apparaît sous double accord et disparaît quand le membre décoche | A | E2E `test_e2e_foire.py::test_visible_par_le_club_double_accord_depuis_le_telephone` |
| 61 | `make bilan` écrit `docs/bilans/bilan-<période>.md` depuis le journal, avec les mêmes chiffres que Suivi (mêmes règles, k = 3), étiqueté « monde de démonstration », sans aucun nom | A | `test_foire_bilan.py::test_les_chiffres_du_bilan_sont_ceux_de_suivi`, `::test_make_bilan_ecrit_le_fichier` |
| 62 | Récit IA du bilan (interrupteur `HACKVS_BILAN_IA`) : le modèle ne reçoit que des agrégats ; tout nombre du récit absent des statistiques (dates exclues) fait rejeter le récit, et le bilan le dit ; panne du modèle → forme déterministe | A (la vérification) ; **aucun récit Apertus réel n'a été généré cette nuit** | `test_foire_bilan.py::test_verifier_recit…`, `::test_recit_du_modele_accepte_rejete_ou_en_panne` (faux fournisseur) |
| 63 | Pipeline Tally : colonnes détectées par leur titre, trois messages fusionnés, doublons retirés, phrases avec e-mail ou téléphone écartées (sortie vérifiée), langue RÉELLE détectée sur le texte (pas la page) ; tourne sans le CSV ; phrases hors dépôt, console en agrégats | A | `test_foire_tally.py` (ingestion, langue, contacts, CSV absent) |
| 64 | **Consentement Tally** : les phrases de la Foire ne passent que par Apertus — tout modèle frontière est refusé par le code avant tout appel | A | `test_foire_tally.py::test_consentement…`, `::test_eval_classification_refuse_un_modele_frontiere…` |
| 65 | Classification contrainte dans la taxonomie (21 métiers FR / DE), abstention permise, sortie validée par le code ; rapport d'agrégats sans aucune phrase ; feuille d'annotation (hors dépôt) avec `metier_attendu` et `domaine` (club / hors_club) ; **aucune exactitude revendiquée** | A (le harnais) ; B pour la mesure Apertus 25/26 acceptées, 8 abstentions (`PREUVES.md`) | `test_foire_tally.py::test_eval_classification_factice…`, `make eval-classification` |

## Vague 2 — « Le Club, c'est vous » (mode salle, interrupteur `HACKVS_SALLE`, allumé par défaut)

| # | Affirmation | Classe | Preuve |
|---|---|---|---|
| 66 | Tout lien et tout QR produit par le serveur part de `PUBLIC_BASE_URL` (puis `HACKVS_URL_PUBLIQUE`, puis l'adresse de la requête) ; aucune URL de domaine en dur | A | `test_url_publique.py`, `test_salle.py::test_qr_salle_part_de_public_base_url` |
| 67 | QR « salle » multi-usage : chaque scan émet un passe individuel signé, rôle invité, 2 heures, sans compte ; plafond configurable (80 par défaut) ; débit limité par passe et globalement (jamais par adresse IP) ; QR refusé tant que la salle n'est pas ouverte | A | `test_salle.py` (QR, plafond, expiration, falsification), balayage `test_autorisation_balayage.py::test_chaque_route_participant…` |
| 68 | Accueil en deux gestes (une capacité + consentement) avec reçu ; sans consentement, rien n'est déclaré | A | `test_salle.py::test_accueil_en_deux_gestes…`, E2E `test_e2e_salle.py` |
| 69 | Demande à trois pièces : le premier oui fournit, les suivants sont en réserve ; l'anneau se ferme sur l'écran géant ; un retrait libère la pièce, la réserve la reprend (recomposition) ; sous 3 porteurs, le rôle n'est pas dit | A | `test_salle.py::test_anneau…`, `::test_role_masque…`, E2E `test_e2e_salle.py::test_le_club_c_est_vous` |
| 70 | Écran géant et bilan en agrégats (k = 3), sans aucun identifiant ; « En N minute(s), cette salle a rendu possible… » | A | `test_salle.py::test_ecran_en_agregats_k3…`, `::test_bilan…`, `::test_parcours_http…` |
| 71 | Retrait déclenché par la télécommande : **simulé en démonstration** (étiqueté à l'écran de la télécommande et dans la réponse) | A | `test_salle.py::test_retrait_declenche_par_la_telecommande…` |
| 72 | Bascule automatique vers la démo scriptée si moins de N participants (`HACKVS_SALLE_MIN`) au bout de 60 s | A (le calcul) ; C (la navigation de l'écran, 5 s après) | `test_salle.py::test_ecran…`, `::test_ouverte_a_l_instant_zero…` |
| 73 | Purge totale en une commande : participants, capacités, réponses, reçus effacés ; la clé de séance change, tout ancien passe et ancien QR est refusé ; l'état n'est jamais écrit dans le journal du Club ; message « Démonstration : vos données sont effacées après la présentation. » sur chaque écran | A | `test_salle.py::test_purge_totale…`, E2E `test_e2e_salle.py` (passe refusé après purge) |
