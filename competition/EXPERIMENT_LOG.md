# Journal d'expériences — sprint d'innovation

Base : gel technique `fb8d88f` (tag local `technical-freeze-v1`). Format : Hypothèse · Baseline · Implémentation ·
Résultat · Cas d'échec · Décision · Preuve. Les hypothèses et baselines sont écrites AVANT l'exécution.

## EXP-A — Échelle d'impact (contact → connexion → activation → persistance ; effet réseau à part)
- **Hypothèse.** On peut mesurer ce qu'une relation est devenue uniquement à partir des faits de la mémoire, sans
  estimation, en séparant ce qui est simulé de ce qui est déclaré.
- **Baseline.** Ce que rapportent les outils d'événements : « nombre de rencontres ».
- **Implémentation.** `adaptateurs/club/impact.py` (niveaux cumulatifs, prédicats sur les faits, persistance = activation
  + étalement ≥ 90 jours + relation actuelle).
- **Résultat (exécuté).** 4 tests + propriété sur 60 historiques aléatoires (entonnoir non croissant, total et réel) : verts.
  Sur le monde de la scène : 18 contacts dont **17 simulés seulement**, 1 connexion, 1 activation, 0 persistance, 0 effet
  réseau. La baseline « nombre de rencontres » aurait affiché 18.
- **Cas d'échec.** Un résultat « utile » est DÉCLARÉ par un membre : l'échelle ne sait pas s'il est vrai.
- **Décision.** KEEP. **Preuve.** `tests/test_impact.py`.

## EXP-B — Observatoire des phénomènes + générateur de réseaux pathologiques
- **Hypothèse.** 7 phénomènes structurels (isolement, concentration, fragmentation, pont fragile, vieillissement,
  sur-sollicitation, entre-soi) sont nommés correctement sur des réseaux à pathologie connue, sans fausse alerte sur un
  réseau sain ; des indicateurs globaux de tableau de bord ne les distinguent pas.
- **Baseline.** Indicateurs globaux (relations, densité, degré moyen) : alerte si l'un s'écarte de plus de 2 écarts-types
  de la référence saine.
- **Implémentation.** `adaptateurs/club/sante.py` (seuils fixés avant exécution), `eval/reseaux_pathologiques.py`.
- **Risque déclaré.** Générateur et seuils sont les nôtres (circularité) → frontière de détection mesurée.
- **Résultat (exécuté, 20 graines × 10 cas).** Après correction d'un ARTEFACT DU GÉNÉRATEUR (les anciennes relations
  actuelles restaient dans l'historique et faisaient paraître tout réseau reconstruit « vieilli ») : aucune pathologie
  manquée ; réseau sain : 0 alerte sur 20. Contre une seconde implémentation indépendante des MÊMES définitions :
  0 alerte sans phénomène réel, 0 phénomène non signalé (preuve de conformité du code, pas de la justesse des définitions).
  Les « alertes en plus » sont des phénomènes co-présents vérifiés (un réseau vieilli est aussi fragmenté).
  Baseline KPI globaux : signale « quelque chose a changé » dans 8/9 pathologies, ne nomme rien, **rate totalement la
  sur-sollicitation (0/20)** et le passage unique dans 3/20.
- **Cas d'échec trouvés en red team.** (1) 6 isolés sur 60 passaient inaperçus (seuil relatif 10 %) → seuil absolu
  « ≥ 3 » ajouté APRÈS la 1re mesure (déclaré). (2) **Deux groupes reliés par UNE personne ayant deux relations de chaque
  côté : aucun signal**, car aucune relation n'est un pont → nouveau phénomène PASSAGE_UNIQUE (point d'articulation,
  personne jamais nommée). (3) Vieillissement : détecté à 70 % d'extinction (20/20), 42 % (9/20), 21 % (0/20).
- **Limite.** Sur la scène (17 membres), 4 phénomènes à la fois : il faudra un ordre de priorité.
- **Décision.** KEEP. **Preuve.** `eval/resultats_observatoire.md`, `tests/test_observatoire.py`.

## EXP-C — Frontière de Pareto des interventions
- **Hypothèse.** Inclusion, cohésion, diversité et réciprocité sont réellement en conflit (corrélations de rang
  négatives ou nulles entre plans non dominés ; rarement un plan idéal) ; les plans simples sont dominés.
- **Baselines.** Hasard (10 tirages), populaires, preuve d'abord, INCLUSION et COHÉSION du cycle 6.
- **Implémentation.** `adaptateurs/club/pareto.py` (glouton sur 35 pondérations du simplexe, évaluation sur 4 axes,
  non dominés, noms fusionnés si identiques), `eval/benchmark_pareto.py`.
- **Résultat (exécuté, 20 réseaux de 150 membres).** Aucun plan n'atteint l'idéal sur tous les axes (0/20). Conflit
  inclusion × cohésion : Spearman **−0,93** (20/20 réseaux). Réciprocité : quasi indépendante (−0,15 / −0,02).
  Front médian : 9 plans ; plans nommés distincts : 3 (extrêmes + équilibre, doublons fusionnés).
- **Hypothèse partiellement FAUSSE.** La diversité sectorielle n'est pas un objectif : 97 % des aides prouvées relient
  déjà deux secteurs (constante d'un plan à l'autre). La non-redondance non plus (99 %). Les deux axes sont retirés :
  **le front est honnêtement en 3 dimensions**.
- **Cas d'échec.** Le front est une APPROXIMATION : 29/200 plans aléatoires de contrôle n'étaient dominés par aucun plan ;
  après élargissement du vivier (30 plans d'exploration, graines distinctes du contrôle) : 19/200. Déclaré.
- **Découverte.** Les plans INCLUSION / COHÉSION du cycle 6 sont dominés par un plan du front dans 13/20 et 11/20 réseaux.
- **Décision.** KEEP (conflit inclusion/cohésion démontré) ; IMPROVE : remplacer la sortie à deux options par le front.
  **Preuve.** `eval/resultats_benchmark_pareto.md`.

## EXP-D — Événements temporels (ce qui a changé et quoi faire maintenant)
- **Hypothèse.** Relation endormie, membre isolé, pont disparu et nouveau groupe se détectent par simple différence de
  deux graphes actuels, sans fausse alerte quand rien ne change.
- **Baseline.** Aucune (le produit actuel ne voit que l'état présent) ; témoin : deux instantanés identiques.
- **Implémentation.** `adaptateurs/club/temporel.py`.
- **Résultat (exécuté).** Événements injectés détectés ; témoin sans changement : 0 événement. Red team : seuil exact
  (90 j : rien ; 91 j : relation endormie + membre isolé), un refus n'est pas un « endormissement », mémoire vide et
  membres inconnus : aucun événement. Sur la scène (60 derniers jours) : 1 nouveau groupe de 7.
- **Décision.** KEEP. **Preuve.** `tests/test_observatoire.py` (6 tests temporels).

## EXP-E — Mémoire des interventions (apprentissage organisationnel EXPLICITE)
- **Hypothèse.** Pour chaque type d'intervention et un contexte explicite, on peut compter ce qui s'est passé APRÈS
  (échelle d'impact), sans attribuer à une intervention un résultat antérieur, et sans taux sur de petits nombres.
- **Baseline.** Aucune mémoire (état du gel).
- **Implémentation.** `adaptateurs/club/bilan.py` ; le type de relance est désormais enregistré aussi quand elle est refusée.
- **Résultat (exécuté).** 4 tests : ventilation par type et contexte, simulé à part, un résultat ANTÉRIEUR n'est jamais
  attribué à l'intervention, pas de taux sous 10 interventions. Sur la scène : 1 introduction et 1 relance
  « réciprocité ouverte », chacune jusqu'à l'activation ; aucune table de soirée (rencontres passées sans plan d'origine).
- **Limite.** NEEDS DATA pour toute conclusion : sur des données de démo, les comptes sont de 1.
- **Décision.** KEEP (mécanisme), NEEDS DATA (enseignements). **Preuve.** `tests/test_bilan.py`.

## EXP-F — Échéancier d'extinction et prévention (contre-factuel temporel « si le Club ne fait rien »)
- **Hypothèse.** Chaque relation actuelle a une date d'extinction connue (dernière interaction + 90 jours, notre règle).
  En projetant ces extinctions SANS prédire aucun comportement (hypothèse pessimiste : aucune interaction spontanée),
  on sait QUAND le réseau perd des membres ou se coupe ; choisir les relations à raviver par leur effet structurel
  marginal sur le réseau projeté préserve plus de réseau que les règles simples, à budget égal.
- **Baselines.** Les plus proches de l'extinction d'abord ; hasard (30 tirages) ; membres les plus reliés d'abord.
- **Mesures (à l'horizon, budget k ravivements).** Membres avec au moins une relation actuelle ; taille du plus grand
  groupe ; nombre de groupes.
- **Règle produit.** L'importance structurelle ne justifie PAS une relance : chaque ravivement indique s'il existe une
  raison prouvée (aide dans un sens au moins) ; sinon l'action proposée est une invitation commune à un événement.
- **Implémentation.** `adaptateurs/club/extinction.py` (projection, prévention gloutonne par gain marginal, variantes
  INCLUSION / COHÉSION, arrêt dès que plus rien ne se perd), `eval/benchmark_extinction.py`.
- **1re mesure : ÉCHEC DE CONCEPTION.** Horizon 90 jours = TOUTES les relations actuelles s'éteignent par définition ;
  avec un plafond de 1, les 5 ravivements donnent le même résultat pour toutes les méthodes (égalité 20/20). Corrigé :
  horizon 30 jours (« que perdons-nous ce mois-ci ? »), plafond 2 identique pour toutes les méthodes.
- **Résultat (20 réseaux de 150 membres, 30 jours, 5 ravivements).** Sans action : 99,7 → 76,7 membres reliés, plus
  grand groupe 37,1 → 11,7. INCLUSION : **86,2** membres reliés (meilleure baseline 81,4 ; gagne 20/20). COHÉSION : plus
  grand groupe **27,7** (meilleure baseline « les plus reliés d'abord » 20,2 ; gagne 18, égalité 2, perd 0). Chaque
  variante PERD sur le critère de l'autre (19/20 et 18/20) : le conflit inclusion/cohésion de EXP-C se retrouve dans le temps.
- **Scène (étape 11).** 15 membres reliés aujourd'hui, 7 dans 30 jours sans action, 13 avec 3 ravivements ; première
  perte le 15 décembre ; **aucun des 3 ravivements n'a de raison prouvée** → action proposée : invitation commune à un
  événement, pas de relance (le principe « se taire sans raison » tient).
- **Cas d'échec / limites.** Projection pessimiste (aucune interaction spontanée) ; la règle des 90 jours n'est pas mesurée.
- **Décision.** KEEP. **Preuve.** `eval/resultats_benchmark_extinction.md`, `tests/test_extinction.py`.
