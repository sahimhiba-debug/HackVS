> ⛔ **OBSOLÈTE — produit d'avant le pivot, ne pas présenter.** Ce dossier décrit l'ancien produit (« intelligence relationnelle »), pas le registre des capacités. La réécriture du pitch est en cours (équipe) ; voir `TODO-DEMO.md`.

# Objections difficiles — et réponses vérifiables

Règle : chaque réponse renvoie à quelque chose que le jury peut exécuter ou lire. Si nous ne savons pas, nous le disons.

| # | Objection | Réponse courte | Vérification |
|---|---|---|---|
| 1 | « Swapcard, Grip ou Brella font déjà ça. » | Ils excellent à recommander pendant l'événement. Nous n'avons pas trouvé dans leurs documents publics de suivi fondé sur une preuve, d'abstention ni de plans d'organisation chiffrés — ce qui ne prouve pas qu'ils n'existent pas. | AUDIT_CHAMPIONNAT § 7 (sources et limites) |
| 2 | « Où est l'IA ? » | Pas dans la démo : la phrase est comprise par des règles vérifiables. L'IA générative a une place mesurable (phrases très libres), sous contrôle du code. Aujourd'hui aucun modèle n'était accessible : nous ne publions aucun chiffre d'IA. | Scène A ; GENAI_RESEARCH.md ; `tests/test_scene.py` (chemin IA avec un double) |
| 3 | « Votre IA est donc inutile ? » | Sur 112 cas, les règles échouent 22 fois, surtout sur les paraphrases et l'allemand libre : c'est la valeur à prouver. L'hybride économe n'appellerait le modèle que sur 37 cas, qui contiennent 19 des 22 échecs. | BENCHMARK_MEMO ; `eval/benchmark_ia.py` |
| 4 | « Tout est fictif. » | Oui, et affiché comme tel. Nous montrons des mécanismes, pas une valeur. La valeur se mesure par un pilote dont le critère d'échec est fixé d'avance. | VALEUR_METIER § 6 |
| 5 | « Vos benchmarks, c'est vous qui définissez la vérité. » | Exact : ils sont synthétiques et nous le disons. Ils servent à attraper des régressions et des idées fausses (plusieurs hypothèses réfutées), pas à promettre un résultat réel. | EXPERIMENT_LOG ; RESEARCH_NOTES |
| 6 | « Le système dit surtout non. » | Il propose quand il peut prouver (Markus, une relance fondée, trois introductions qui réunissent les îlots). Une relance sans raison fatigue un réseau ; le silence est compté. | Scène, étapes 2 et 7 |
| 7 | « Et si les membres ne remplissent rien ? » | Alors le système se tait, ce qui est honnête mais sans valeur. C'est le premier indicateur du pilote : moins d'un volontaire sur cinq qui publie un besoin = échec. | VALEUR_METIER § 5–6 |
| 8 | « Le Pareto, c'est du jargon. » | À l'écran : deux plans, deux chiffres. « Reliés ensemble » contre « résistent à la perte d'une relation ». Le reste est en annexe. | Scène B, étape 5 |
| 9 | « Votre front est-il optimal ? » | Non : approché (glouton pondéré + heuristiques). Le gain de chaque plan est exact ; l'exhaustivité ne l'est pas. | ANNEXE_TECHNIQUE § 6 ; `adaptateurs/club/pareto.py` |
| 10 | « Ça passe à l'échelle ? » | Recherche en 221 ms à 1000 membres générés. Le diagnostic complet prend 24 s à 1000 membres (croissance plus que linéaire) : c'est une limite connue ; à 10 000 membres il faudrait le calculer en tâche de fond, pas à la demande. | `eval/resultats_perf_echelle.md` ; ANNEXE § 4 |
| 11 | « Et la vie privée ? » | Invisible par défaut ; coordonnées après double accord ; un refus n'est jamais contourné ; qui refuse n'est ni nommé ni compté (moins de 3). Ce sont des tests, pas des promesses. | `tests/test_scene.py`, `tests/test_adversarial_sprint.py`, registre C02–C04 |
| 12 | « L'organisatrice voit tout : c'est de la surveillance. » | Elle voit des relations nées d'événements du Club et des introductions consenties, jamais de messages ni de données externes. Les rôles authentifiés ne sont pas encore implémentés : c'est une limite. | 16_LIMITATIONS |
| 13 | « Qu'avez-vous fait pendant le hackathon ? » | Seulement ce qui est listé avec un commit postérieur au début officiel. Le reste a été préparé avant, et nous le disons. | CONTRIBUTIONS_HACKATHON.md ; `git log` |
| 14 | « Et si le réseau de la salle tombe ? » | Tout tourne en local, sans dépendance externe ; vidéo de secours de la même scène. | 09_DEMO_SCRIPT, plans B |
| 15 | « Pourquoi pas un CRM ? » | Un CRM suit les relations d'une organisation avec ses clients, pas les relations des membres entre eux, ni le consentement de deux tiers à être présentés. | VALEUR_METIER § 4 |
| 16 | « Combien de temps économisé ? » | Nous ne le savons pas : nous n'avons pas mesuré la pratique actuelle. Le pilote mesure les minutes de l'organisatrice. | VALEUR_METIER § 3 |
