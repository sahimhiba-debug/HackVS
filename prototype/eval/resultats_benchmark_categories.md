# Benchmark du matching par catégorie (données FICTIVES, cas écrits avant exécution)

Moteur contre référence « mots-clés + mêmes filtres ». Réussi = bon résultat dans le top 3 (ou abstention attendue), sans violation de contrainte.

| Jeu | Cas | WIN | LOSS | TIE (2 justes) | TIE (2 faux) | Abstentions attendues : moteur juste |
|---|---|---|---|---|---|---|
| base | 20 | 11 | 0 | 9 | 0 | 4/4 |
| adversarial (ADVERSARIAL) | 20 | 9 | 0 | 11 | 0 | 7/7 |
| reserve | 14 | 5 | 0 | 9 | 0 | 2/2 |
| reserve2 | 18 | 9 | 0 | 9 | 0 | 3/3 |
| reserve3 | 20 | 7 | 2 | 5 | 6 | 5/5 |
| reserve4 | 20 | 2 | 4 | 4 | 10 | 4/5 |
| **total** | 112 | 43 | 6 | 47 | 16 | 25/26 |

Cas où le moteur échoue (22) :
- reserve3 / r3_bouteilles_au_frais (paraphrase)
- reserve3 / r3_cueillette (paraphrase)
- reserve3 / r3_google (paraphrase)
- reserve3 / r3_mise_en_bouteille (paraphrase)
- reserve3 / r3_de_website (allemand libre)
- reserve3 / r3_en_accountant (anglais)
- reserve3 / r3_preter_argent (paraphrase)
- reserve3 / r3_photo_culinaire (paraphrase)
- reserve4 / r4_yaourts_zurich (paraphrase)
- reserve4 / r4_videurs (paraphrase)
- reserve4 / r4_vendangeurs (paraphrase)
- reserve4 / r4_toit_courant (paraphrase)
- reserve4 / r4_visibilite_web (paraphrase)
- reserve4 / r4_retraite_pme (paraphrase)
- reserve4 / r4_de_logistik (allemand libre)
- reserve4 / r4_en_website (anglais)
- reserve4 / r4_en_security_event (anglais)
- reserve4 / r4_emprunt (paraphrase)
- reserve4 / r4_ordis_lents (paraphrase)
- reserve4 / r4_video_promo (paraphrase)
- reserve4 / r4_camion_neuf (faux ami)
- reserve4 / r4_graphiste_logo (paraphrase)

## Comportements (tests exécutés maintenant)

| Catégorie | Test | Résultat |
|---|---|---|
| COLD START (nouveau membre) | `test_nouveau_membre_invisible_par_defaut_puis_visible_s_il_le_choisit` | PASS |
| SATURATION (membre sur-sollicité) | `test_budget_d_attention_un_membre_ne_recoit_pas_huit_relances_le_meme_jour` | PASS |
| CONTRADICTION (historique) | `test_un_refus_ancien_n_ecrase_pas_une_relation_devenue_vivante` | PASS |
| RECIPROCITY FAILURE (dite, pas inventée) | `test_nouveau_membre_reciprocite_prouvee_et_non_prouvee` | PASS |
| COHÉRENCE explication = décision | `test_coherence_decision_explication_sur_tous_les_membres` | PASS |
