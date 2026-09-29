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

## EXP-G — Sérendipité structurelle : similarité contre complémentarité prouvée
- **Hypothèse.** Recommander par SIMILARITÉ de profil (ce que font la plupart des outils de networking) apparie surtout
  des membres du même secteur ; notre moteur, fondé sur une AIDE PROUVÉE (l'offre de l'un couvre la recherche de
  l'autre), apparie des secteurs différents — sans aucun objectif de diversité ajouté.
- **Baseline.** Top-1 par similarité TF-IDF des textes de profil (et top-3).
- **Mesure.** Part des paires recommandées dont les familles de secteur diffèrent ; part des paires où une aide est prouvée.
- **Résultat (exécuté, 33 membres, top 3).** SIMILARITÉ : 72 paires, **86 % entre secteurs différents**, 8 % avec aide
  prouvée, quelqu'un pour 33/33 membres. COMPLÉMENTARITÉ : 25 paires, 100 % entre secteurs différents, 100 % avec aide
  prouvée, 17/33 membres (abstention pour 16). 5 paires communes.
- **Hypothèse RÉFUTÉE.** La similarité n'enferme PAS dans le même secteur sur nos profils : l'argument « les autres
  vous présentent vos semblables » est faux ici et ne doit pas être utilisé. La différence réelle : **92 % des
  recommandations par similarité n'ont aucune aide prouvée**.
- **Décision.** DELETE l'idée « sérendipité par diversité sectorielle » (aucun mécanisme à ajouter) ; KEEP le fait mesuré
  (preuve vs similarité). Limite : 33 profils fictifs, écrits par nous. **Preuve.** `eval/resultats_serendipite.md`.

## EXP-H — Diagnostic d'organisation : la boucle complète en une vue
- **Hypothèse.** Les modules A–F s'assemblent en une vue unique (comprendre → diagnostiquer → voir venir → agir →
  observer → se souvenir) utilisable à la taille du Club, sans écriture, avec « ne rien faire » quand rien n'est prouvé.
- **Implémentation.** `adaptateurs/club/diagnostic.py`, route `/api/reseau/diagnostic` (organisation, démo). Phénomènes
  triés par priorité (choix de produit déclaré : ce qui prive des membres de toute relation d'abord). Le front de Pareto
  remplace les deux options du cycle 6 (dominées dans 13/20 et 11/20 réseaux, EXP-C).
- **Défauts trouvés en l'exécutant.** (1) Pareto sans aucune action : un « plan vide » annoncé idéal et baptisé de
  quatre noms → NE_RIEN_FAIRE explicite. (2) À 500 membres : KeyError, une relation menacée touchant un NON-membre
  (exposant) → filtrée à la source (test rouge vérifié). (3) 5,2 s à 150 membres (204 s à 1000) : `calculer_aides` appelé
  deux fois et reconnaissance de concepts recalculée sur les mêmes textes → une seule fois + mémorisation (fonction pure).
- **Résultat.** 150 membres : **0,67 s** ; 500 : 5,8 s ; 1000 : 25 s. Sur la scène : 101 ms, 4 phénomènes triés, un seul
  plan non dominé (pas de conflit sur ce petit réseau : dit, pas inventé). Non-régression : 201 tests, 20/20, benchmark
  de matching par catégorie IDENTIQUE à l'octet près.
- **Décision.** KEEP. **Preuve.** `tests/test_diagnostic.py`, `tests/test_extinction.py`.

## EXP-I — Boucle fermée : prévu contre réalisé (simulation auditée par les faits)
- **Hypothèse.** Parce que la mémoire est un journal rejouable, on peut enregistrer une décision d'organisation (plan
  choisi + projection supposant 100 % d'acceptation), puis reconstruire le réseau À LA DATE de la décision et mesurer,
  action par action et sur des faits RÉELS seulement, ce qui s'est produit — et donc l'écart entre projection et
  réalité. Les comptes observés tempèrent les projections suivantes, sans modèle statistique.
- **Baseline.** Aujourd'hui (et dans les outils usuels) : projection jamais confrontée à la réalité.
- **Critères.** Aucun résultat attribué sans fait réel postérieur à la décision ; refus comptés à part ; rejeu identique ;
  pas de taux sous 10 actions.
- **Implémentation.** `adaptateurs/club/boucle.py` ; routes `/api/reseau/decision` (n'accepte que des actions
  ACTUELLEMENT proposables : preuve, consentement, pas de refus — sinon 409) et `/api/reseau/decisions` ; historique
  intégré à « se souvenir » du diagnostic.
- **Résultat (exécuté).** 6 tests : réseau reconstruit à la date de la décision ; issue de chaque action (réalisée sur
  fait RÉEL, refusée, simulée seulement, sans suite) ; prévu inclusion 3 contre réalisé 1 sur le cas construit ; un fait
  antérieur n'est pas un résultat ; le fait le plus récent gouverne (refus puis connexion = réalisée) ; plan vide ou
  invalide refusé ; pas de taux sous 10 actions ; rejeu identique ; l'API refuse une action avec un membre fermé.
- **Limites.** NEEDS DATA : aucune décision réelle ; la réciprocité réalisée n'est pas observable (dite).
- **Décision.** KEEP (mécanisme). **Preuve.** `tests/test_boucle.py`.

## EXP-J — Cohésion ROBUSTE : le grand réseau « en fil de fer »
- **Hypothèse 1 (robustesse = fragilités supprimées, comme 4e axe).** Varie entre plans (7 à 10 valeurs) mais
  colinéaire à l'inclusion (ρ = +0,91) → REJETÉE comme axe.
- **Découverte (effet de second ordre).** Sur 10 réseaux, un plan COHÉSION de 10 actions construit un plus grand groupe
  de 60,9 membres mais **crée 15,4 nouveaux ponts fragiles** (6 à 23) : seuls **6,7** membres restent reliés si UNE
  relation quelconque s'éteint. Maximiser la taille construit un réseau en fil de fer.
- **Mécanisme.** Cohésion ROBUSTE = taille du plus grand groupe 2-arête-connexe (survit à la perte de n'importe quelle
  relation). Gain marginal exact et rapide par l'ARBRE DES PONTS (ajouter u–v fusionne les groupes robustes du chemin
  u→v) ; **0 désaccord avec la force brute** sur 300 graphes aléatoires ; glouton 6,5 s → intégré au front sans surcoût notable.
- **Résultat.** Variante robuste contre cohésion simple (10 réseaux) : plus grand groupe robuste **28,1 contre 6,7**,
  ponts fragiles **−4,4 contre +15,4**, inclusion 4,1 contre 0,3 ; plus grand groupe 34,6 contre 60,9 (la cohésion simple
  gagne sur SON critère). Comme 4e axe du front : indépendant de la cohésion simple (ρ = −0,03), en conflit avec
  l'inclusion (−0,47) ; front médian 21 plans ; aucun plan idéal (0/20) ; hasard de contrôle dominé 167/200.
- **Décision.** KEEP : axe COHÉSION_ROBUSTE dans le front. **Preuve.** `tests/test_observatoire.py`
  (cas construit + égalité rapide/brute), `eval/resultats_benchmark_pareto.md`.
- **Performance.** Diagnostic à 4 axes : 2,1 s à 150 membres (80 % dans les chemins de l'arbre des ponts) → arbres
  enracinés une fois, somme de chemin par ancêtre commun : **1,24 s** (500 membres : 17,7 → 10,3 s) ; exactitude
  revérifiée contre la force brute : 0 désaccord sur 4171 vérifications.

## EXP-K — Prévention temporelle ROBUSTE (appliquer EXP-J à l'échéancier) — DELETE
- **Hypothèse.** Raviver en priorité ce qui préserve le plus grand groupe robuste bat les baselines sur ce critère.
- **Résultat (20 réseaux, 30 jours, 5 ravivements).** PERD : groupe robuste 2,30 contre 2,75 (« plus reliés d'abord ») ;
  gagne 1, égalité 16, perd 3 ; n'utilise que 0,3 ravivement sur 5.
- **Cause comprise.** (1) Myopie du glouton : reconstituer un cycle exige souvent DEUX ravivements simultanés ; chacun
  seul a un gain nul → arrêt. (2) Réseaux générés arborescents : groupes robustes minuscules (5,4 aujourd'hui).
- **Décision.** DELETE (code retiré, rien de gardé « parce que cela a demandé du travail »). Piste non explorée : gain par
  PAIRES de ravivements (coût quadratique) — DEFER.

## Red team du sprint — générateur pathologique contre Pareto et prévention
- **Attaque.** 9 réseaux pathologiques + sain, candidates aléatoires : déterminisme, front non dominé, aucune action
  inventée, plafond respecté même pour un hub ; prévention : seulement des relations menacées, plafond ; cas vides.
- **Résultat.** 20 tests verts — **aucun défaut trouvé** (résultat négatif consigné). Preuve : `tests/test_adversarial_sprint.py`.

## EXP-L — Invitation ciblée : qui inviter personnellement à la prochaine soirée ?
- **Hypothèse.** Parmi les membres dormants/isolés (qui acceptent les introductions), choisir B invités par un couplage
  EXACT (flot maximal : chaque invité doit avoir une aide prouvée avec un présent ; chaque présent accueille au plus c
  rencontres) garantit plus d'invités effectivement « servis » que des règles simples, à budget égal.
- **Baselines.** Hasard (30 tirages) ; « le plus d'aides possibles d'abord » ; « inactif le plus récemment d'abord ».
- **Hypothèse déclarée.** Les membres ACTIFS (au moins une relation actuelle) sont supposés présents.
- **Implémentation.** `adaptateurs/club/invitations.py` (b-couplage biparti par flot maximal à coût minimal, budget
  plafonné), intégré à la section « agir » du diagnostic ; `eval/benchmark_invitations.py` (juge commun : le même flot sur
  les invités choisis par chaque méthode).
- **Résultat.** Grande soirée (tous les actifs présents) : **égalité 20/20** avec « le plus d'aides d'abord » — la
  sophistication n'apporte RIEN quand les hôtes abondent. Petite soirée (15 présents, capacité 1, 15 invitations) :
  **gagne 7, égalité 13, perd 0** ; 9,30 invités servis contre 8,65 (hasard 5,74) — chiffres du script
  reproductible (une sonde ponctuelle antérieure, avec un autre tirage des présents, donnait 9/11 : non retenue). Optimalité vérifiée contre la force
  brute (60 instances) ; capacité, budget, preuve et abstention testés.
- **Décision.** KEEP, avec une affirmation modeste : optimal par construction ; utile seulement quand les hôtes sont rares.

## EXP-M — « Quelle intervention serait pertinente MAINTENANT ? » (événements temporels → actions prouvées ou silence)
- **Hypothèse.** Chaque changement observé (relation endormie, membre isolé, pont disparu, nouveau groupe) peut recevoir
  des actions fondées sur une aide PROUVÉE — ou un silence explicite ; la plupart des changements n'ont PAS de raison
  prouvée d'agir.
- **Baseline.** Un CRM : relancer à chaque changement (100 % de sollicitations, sans raison).
- **Implémentation.** `diagnostic._actions_maintenant` (INVITER un membre isolé s'il a une rencontre prouvée possible ;
  RAVIVER_AVEC_RAISON une relation endormie seulement si une aide est prouvée ; RECRÉER_UN_PONT parmi les actions
  proposables entre morceaux) ; consentement vérifié (test).
- **Résultat (10 réseaux générés de 150 membres, 30 derniers jours).** 254 relations endormies : **16 (6 %) avec une
  raison prouvée**, silence pour 238. 166 membres devenus isolés : 97 (58 %) invitables avec une rencontre prouvée.
- **Limite.** « Raison prouvée » = aide dans un sens au moins ; une relation peut avoir d'autres bonnes raisons que le
  système ignore (dit).
- **Décision.** KEEP. **Preuve.** `tests/test_diagnostic.py::test_chaque_changement_recoit_une_action_prouvee_ou_le_silence`.

## EXP-N — La boucle sur trois mois : fait-elle mieux que ne rien faire ?
- **Hypothèse.** Jouée chaque mois (diagnostic → plan ÉQUILIBRE → décision enregistrée → une part des actions acceptée
  → vieillissement), la boucle garde plus de membres reliés et un plus grand groupe robuste que le même réseau sans
  action — même avec un taux d'acceptation faible — et le bilan prévu/réalisé retrouve exactement ce qui a été accepté.
- **Baseline.** Le même réseau, les mêmes mois, sans aucune action.
- **Hypothèses déclarées.** Taux d'acceptation SIMULÉ (30 %, 60 %, 100 %), tirage reproductible ; une action acceptée
  produit une introduction acceptée ; aucune autre interaction.
- **Implémentation.** `eval/simulation_boucle.py` (5 réseaux de 120 membres, 3 mois, plan ÉQUILIBRE de 5 actions).
- **Défaut trouvé par le contrôle d'intégrité.** Le bilan comptait 5,8 réalisations pour 5,0 acceptations (30 %) :
  double attribution d'une acceptation à deux décisions sur la même paire → FAILURES n° 38, corrigé ; après correction,
  réalisé selon le bilan = accepté **exactement** (5,0 / 8,4 / 15,0), figé dans un test.
- **Résultat** (régénéré après EXP-O, l'hystérésis modifiant le plan choisi d'un mois à l'autre). Membres reliés en fin
  de période : sans action **1,4** ; boucle à 30 % **9,8** ; 60 % **14,0** ; 100 % **19,6**. Plus grand groupe robuste : 1,0 / 1,0 / 1,6 / 5,0 — le plan ÉQUILIBRE construit peu de robustesse.
- **Lecture honnête.** Monde pessimiste (aucune interaction spontanée : sans action, presque tout s'éteint) ; le gain est
  mécanique (des actions acceptées créent des relations). Ce qui est démontré : la boucle fonctionne de bout en bout,
  et son bilan est EXACT par rapport à ce qui s'est passé.
- **Décision.** KEEP (preuve d'intégrité). **Preuve.** `eval/resultats_simulation_boucle.md`, `tests/test_boucle.py`.
- **Comparaison de politiques sur une saison (60 %, 3 mois, 5 réseaux) — INCONCLUSIVE.** Membres reliés : INCLUSION
  18,2 ; ÉQUILIBRE 14,0 ; RÉCIPROCITÉ 13,6 ; COHÉSION 13,4 ; ROBUSTE 13,2 (valeurs régénérées après EXP-O). Groupe robuste ≈ 1 partout. Dans un monde
  sans interaction spontanée ni soirée, 5 actions par mois ne maintiennent pas un réseau de 120 membres : les
  interventions ciblées sont MARGINALES face aux événements. Comparer des politiques exigerait de simuler aussi les
  soirées (hypothèses empilées) : non fait. Aucune recommandation de politique n'est tirée de cette mesure.

## EXP-O — Stabilité des recommandations (une rencontre de plus ne doit pas tout changer)
- **Hypothèse.** Une perturbation minimale du réseau (UNE relation actuelle ajoutée, hors des actions proposées) laisse
  les plans nommés du front largement inchangés (recouvrement de Jaccard élevé) ; une instabilité révélerait un
  départage arbitraire.
- **Baseline.** Deux plans tirés au hasard parmi les mêmes candidates (recouvrement attendu par hasard).
- **Résultat (10 réseaux × 6 perturbations d'UNE relation).** Recouvrement moyen avec le plan d'avant : INCLUSION **0,96**
  (identique 27/30) ; COHÉSION 0,80 ; RÉCIPROCITÉ 0,76 ; ROBUSTE 0,73 ; ÉQUILIBRE **0,70** (plan changé de plus de
  moitié dans 11/30) ; hasard 0,00. 54/60 perturbations sont STRUCTURELLES (réseau clairsemé) : l'essentiel de
  l'instabilité est légitime ; RÉCIPROCITÉ et ÉQUILIBRE changent aussi sans changement de structure (départage arbitraire).
- **Remède testé : hystérésis** (parmi les plans à égalité ou à ε de regret près, préférer le plus proche de la DERNIÈRE
  décision). Courbe : ε = 0 → 0,71 ; **ε = 0,1 → 0,76** (regret perdu moyen 0,006, max 0,1) ; ε = 0,3 → 0,77 (0,026).
- **Décision.** KEEP modeste (ε = 0,1, seulement si une décision précédente existe) ; gain faible, dit comme tel.
  **Preuve.** `tests/test_observatoire.py::test_hysteresis…`.

## Reproductibilité du sprint
- `python scripts/reproduire_sprint.py` rejoue les 7 benchmarks du sprint (≈ 4 min). Première exécution : 6 fichiers
  identiques à l'octet ; 1 fichier (simulation de la boucle) PÉRIMÉ par rapport au code — généré avant l'hystérésis
  (EXP-O) — régénéré, chiffres corrigés ci-dessus ; deux exécutions successives identiques (déterminisme vérifié).
