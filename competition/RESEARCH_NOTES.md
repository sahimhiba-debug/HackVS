# Notes de recherche — sprint d'innovation (après le gel technique)

Base de comparaison : gel technique, commit `fb8d88f` (tag local `technical-freeze-v1`). Retour possible à tout moment :
`git checkout fb8d88f`. Toute expérience est comparée à cette base et doit laisser passer toute la suite existante.

## Question directrice
« Un ingénieur du jury a vu 100 projets de networking avec IA. Qu'est-ce qui le ferait prendre celui-ci au sérieux ? »
Hypothèse de travail : pas une meilleure liste de contacts, mais une organisation qui **voit** l'état de son réseau,
**comprend** ce qui change dans le temps, **choisit** entre des objectifs en conflit, et **se souvient** de ce que ses
interventions ont réellement produit — sans apprentissage automatique, avec des faits.

## Tri des idées (test des 4 jours)

| Idée | Problème du Club | Mécanisme | Preuve possible | Démo | Risque | Coût | Verdict initial |
|---|---|---|---|---|---|---|---|
| **Échelle d'impact** (contact → connexion → activation → persistance → effet réseau) | Le Club ne sait pas si ses soirées produisent autre chose que des cartes échangées | Définitions sur les FAITS de la mémoire (aucune estimation) | Tests par niveau, historiques générés, cohérence avec l'état de relation | Un entonnoir de faits, pas un score | Confondre « déclaré » et « vrai » | Faible | BUILD |
| **Observatoire des phénomènes** (isolement, concentration, silos, pont fragile, vieillissement, sur-sollicitation, entre-soi) | Un tableau de 30 KPI ne dit pas quoi faire | Détecteurs structurels + intervention associée | Générateur de réseaux PATHOLOGIQUES à vérité connue ; baseline « KPI globaux » | « Votre réseau tient à une seule relation » | Désigner des personnes (notation sociale) → observations agrégées, sans nom côté membres | Moyen | BUILD |
| **Frontière de Pareto des interventions** | « Le meilleur plan » cache des choix de valeurs | Plans issus d'objectifs réellement distincts, évalués sur tous les axes, non dominés conservés | Taille du front, plans dominés éliminés, baselines placées sur le graphique | « Aucun plan ne maximise à la fois inclusion et cohésion » | Front artificiel (objectifs corrélés) → mesurer la corrélation | Moyen | BUILD |
| **Événements temporels** (relation qui s'endort, membre qui s'isole, pont qui disparaît, groupe qui se scinde) | Le Club découvre les problèmes trop tard | Différence entre deux instantanés du graphe actuel | Chronologies générées avec événements injectés : rappel / fausses alertes | « Depuis 60 jours, le pont entre deux groupes a disparu » | Alertes trop nombreuses → seuils déclarés | Faible | BUILD |
| **Mémoire des interventions** (apprentissage organisationnel explicite) | Le Club refait les mêmes actions sans savoir ce qui a marché | Journal intervention → résultat observé (échelle d'impact) → contexte ; comptes, jamais une prédiction | Tests ; k-anonymat des comptes | « Les 5 dernières présentations par un intermédiaire : 3 relations encore actives » | Petits nombres présentés comme des taux → afficher des comptes | Faible | BUILD après l'échelle |
| Sérendipité contrôlée | Les recommandations par similarité enferment | Aide prouvée + communautés différentes + faible redondance | Intégrée comme objectif « diversité » du Pareto | « Vous ne vous ressemblez pas : c'est pour ça » | Justification creuse | Faible si intégrée | DELETE (EXP-C, EXP-G : la diversité sectorielle ne discrimine rien ; la similarité ne l'enferme pas non plus) |
| Événement thématique proposé | Choisir le thème de la prochaine soirée | Thème qui couvre le plus de besoins non servis + ponts | Comparaison avec thème « le plus fréquent » | Oui | Recouvre le plan de soirée existant | Moyen | DEFER |
| Modèle ML de prédiction d'acceptation | — | — | Aucune donnée réelle pour l'entraîner | — | Fabriquerait de la confiance | — | REJECT |
