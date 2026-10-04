# Lot 7 — L'IA Apertus

> **Construit — branche `annee-1`, pas dans la démo** pour ce qui est nouveau cette nuit (le suivi du taux
> d'acceptation, interrupteur `HACKVS_SUIVI_IA`). Le reste du lot avait déjà été construit et mesuré AVANT la mission ;
> il est rappelé ici avec ses preuves, sans rien y ajouter. Apertus 1.5, servi par le CSCS.

| Demandé par la mission | État | Preuve |
|---|---|---|
| Appel d'outil natif pour l'extraction, mesuré sur les 26 cas, à côté des anciens chiffres | **fait avant la mission** : 1/26 juste, aucun gain sur la consigne seule (1/26) ; plus de sorties fausses acceptées (3) ; l'interrupteur `APERTUS_APPEL_OUTILS` reste éteint | CLAIMS 89, `prototype/eval/resultats_banc/apertus-outils.md` ; anciens chiffres : CLAIMS 39 (ce que voit le membre : 17/26, règles seules 16/26) |
| Coach de demande SMART | **fait avant la mission** (règles FR / DE ; questions qui manquent : quand, combien, où) | CLAIMS 91 |
| Classification par métier | **harnais fait et passé sur Apertus** (26 cas : 25 sorties acceptées, 8 abstentions ; 21 phrases de la Foire) — **aucune exactitude revendiquée** : la feuille d'annotation humaine n'est pas remplie | `prototype/eval/resultats_classification/` |
| Pipeline d'affinage prêt à entraîner (données synthétiques, filtrage, LoRA, évaluation sur le jeu humain figé) | **fait avant la mission, entraînement NON lancé** | CLAIMS 101, `prototype/finetune/` |
| Suivi du taux de propositions acceptées | **construit cette nuit** : chaque compréhension proposée (par le modèle, ou par les règles en repli) et chaque confirmation sont deux faits sans contenu ; le taux par source se lit dans la console du secrétariat, « < 3 » compté en entreprises | `test_annee1_suivi_ia.py` · CLAIMS 111 |
| Parité IA ON / OFF | **fait avant la mission** | CLAIMS 7, 82 (`test_parite_ia.py`, non vacueuse) |
| Voix, Apertus Mini (expérimental) | **non fait** | — |

**Vérifié cette nuit, pour de vrai.** L'API d'Apertus (CSCS, `swiss-ai/Apertus-v1.5-70B`) répond depuis la session :
un appel trivial a répondu (sortie lue dans la session, non conservée comme preuve). Aucun nouveau chiffre de qualité n'est publié ici : le banc des 26 cas n'a pas été
relancé (son protocole interdit de le rejouer pour « améliorer » un résultat publié).
