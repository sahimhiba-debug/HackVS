> ⛔ **OBSOLÈTE — produit d'avant le pivot, ne pas présenter.** Ce dossier décrit l'ancien produit (« intelligence relationnelle »), pas le registre des capacités. La réécriture du pitch est en cours (équipe) ; voir `TODO-DEMO.md`.

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

## Bilan d'étape du sprint (état au commit courant ; détails et chiffres : EXPERIMENT_LOG.md)

**BASELINE.** Gel technique `fb8d88f` (tag local `technical-freeze-v1`) : 166 tests, matching par preuves, relances
fondées, optimiseur de soirée, confidentialité par inférence.

**PERCÉES (gardées, mesurées, attaquées).**
1. *Le réseau en fil de fer* (EXP-J) : maximiser la taille du réseau crée des ponts fragiles (+15,4 par plan) ; la
   cohésion ROBUSTE (groupe qui survit à la perte de n'importe quelle relation) donne un groupe robuste 4,2× plus grand.
   Gain exact par l'arbre des ponts, vérifié contre la force brute.
2. *Il n'existe pas de meilleur plan* (EXP-C/J) : front de Pareto à 4 axes, aucun plan idéal (0/20), conflit
   inclusion/cohésion mesuré ; deux axes « attendus » (diversité, non-redondance) réfutés et retirés.
3. *Voir venir* (EXP-F) : date de la première perte « si le Club ne fait rien », ravivements qui préservent le réseau ;
   la règle « pas de relance sans raison » tient (invitation plutôt que relance).
4. *Simulation auditée par les faits* (EXP-I) : décision enregistrée, confrontée au réseau reconstruit à sa date.
5. *Diagnostic d'organisation* (EXP-H) : la boucle complète en une vue, 1,24 s pour 150 membres, « ne rien faire » quand
   rien n'est prouvé.
6. *Consentement à deux niveaux* : trois violations trouvées en red team (dont une antérieure au gel), corrigées ;
   invariant de classe testé sur des réseaux générés avec retraits et refus aléatoires.

7. *Chaque changement → une action prouvée, ou le silence* (EXP-M) : 94 % des relations endormies n'ont aucune raison
   prouvée d'être relancées — un CRM les relancerait toutes.
8. *Bilan exact* (EXP-N) : la boucle jouée sur trois mois retrouve exactement les acceptations (double attribution
   trouvée et corrigée) ; *reproductibilité* : tous les benchmarks rejoués en CI, échec si un résultat publié diverge.

**GARDÉS AVEC UNE AFFIRMATION MODESTE.** Invitation ciblée (EXP-L : utile seulement quand les hôtes sont rares) ;
hystérésis (EXP-O : +0,05 de stabilité).

**REJETS (mesurés).** Sérendipité par diversité sectorielle (EXP-G : hypothèse réfutée) ; robustesse par comptage comme
axe (colinéaire) ; prévention robuste (EXP-K : perd contre la baseline) ; ML (aucune donnée).

**LIMITES.** Toutes les mesures de réseau sont SYNTHÉTIQUES ; « 90 jours », « 3 relances par jour » sont des hypothèses ;
l'invitation ciblée n'apporte rien quand les hôtes abondent ; la boucle prévu/réalisé attend des données réelles.
