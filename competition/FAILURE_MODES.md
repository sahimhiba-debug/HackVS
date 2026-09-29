# Modes de défaillance (Défaillance → Détection → Reprise → Impact utilisateur → Test)

| Défaillance | Détection | Reprise | Impact utilisateur | Test |
|---|---|---|---|---|
| LLM en panne, refus, JSON invalide | exception / validation du schéma | une relance avec l'erreur, puis repli sur les règles, signalé | « analyse par règles » affiché ; aucune invention | `test_parcours.py::test_panne_refus_ou_json_invalide_repli_visible`, `test_apertus_en_panne_repli_visible` |
| Aucun candidat prouvé | aucune suggestion au-dessus du seuil | abstention explicite | « personne ne correspond avec preuve » plutôt qu'une liste | `test_scene.py` (étape 5), C01 |
| Problème d'optimisation vide | 0 participant / 0 arête | abstention propre | pas de plan, raison affichée | S09, `test_aucun_participant_abstention_sans_plantage` |
| Contrainte obligatoire levée par la demande | politique à la compilation | escalade vers l'humain | l'organisateur doit décider | S04, S05 |
| Refus d'introduction contourné par une table | validateur indépendant + règle bloquante | paire exclue du problème | aucune table commune | `test_humain.py` |
| Relation ancienne prise pour actuelle | `graphe_actuel` (règle unique d'état) | lien ignoré pour agir, gardé en mémoire (« à raviver ») | pas de présentation fondée sur un lien mort | `test_temporel.py` |
| Deux écrivains sur la même mémoire | (max seq, nombre) à chaque lecture | resynchronisation / relecture complète | aucune donnée périmée | `test_cache_de_la_memoire_exact_face_a_un_autre_ecrivain` |
| Double clic / double soumission | machine à états du magasin (verrou) | 409 dès la 2e | une seule transition | `test_securite_api.py::test_double_soumission_une_seule_transition` |
| Tiers qui agit sur une relation | contrôle de participation AVANT l'état | 403 sans état ni nom | rien n'est appris | `test_un_tiers_ne_peut_faire_aucune_transition…` (8 cas) |
| Entrée surdimensionnée ou malformée | bornes des modèles d'entrée | 422 | message clair, service debout | `test_toutes_les_entrees_sont_bornees`, introspection |
| Branche / stress sur une exécution sans spécification | `parent.spec is None` | `ErreurSpec` (409 par l'API) | message explicite | `test_branche_et_stress_sur_une_execution_sans_specification…` |
| Réinitialisation de la démo | vidage magasin + mémoire | état cohérent | aucun fait orphelin | `test_reinitialisation_ne_laisse_aucun_fait_orphelin` |
| Double clic sur « suivant » de la scène | verrou + 409 en fin | une étape | démo stable | `test_scene.py`, navigateur |
| Mode réel sans source autorisée | configuration | 503 / 501, rien de simulé | aucune fausse donnée | `test_mode_reel_ne_simule_rien` |
| Deux soirées le même jour / plan devenu faux après approbation | contrôle à l'enregistrement | refus explicite (409) : « collision » ou « plan périmé : relancez » | aucune rencontre impossible ni refus contourné | `test_collisions.py` |
| Aucune action prouvée possible | front vide / candidates vides | NE_RIEN_FAIRE explicite | pas de « plan vide idéal » | `test_pareto_sans_aucune_action_prouvee_ne_rien_faire` |
| Relation avec un non-membre dans le réseau | filtre membres à la source | ignorée | pas de plantage | `test_une_relation_avec_un_non_membre…` |
| Décision contenant une action non proposable | contrôle à l'enregistrement | 409 | aucune décision contournant le consentement | `test_api_decision_n_accepte_que…` |
| Même paire décidée deux fois | fenêtre fermée par la décision suivante | issue « remplacée » | bilan exact | `test_un_resultat_n_est_attribue_qu_a…` |
| Changement observé sans raison prouvée | aucune aide prouvée | silence explicite | pas de relance de politesse | `test_chaque_changement_recoit_une_action…` |
