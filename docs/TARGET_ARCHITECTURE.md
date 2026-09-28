# Architecture cible : Valais Ecosystem OS

**Principe** : les agents proposent, le code déterministe vérifie, la politique contrôle, l'humain décide. Tout
résultat important est une **exécution de décision** enregistrée, rejouable et certifiée à partir d'enregistrements
structurés, jamais d'un résumé libre.

## 1. Découpage : plateforme générique / adaptateur de challenge

```
prototype/
  plateforme/          GÉNÉRIQUE, aucune donnée du Club ni du challenge
    affirmations.py      registre d'affirmations (Claim Ledger) : statut, source, validité, fraîcheur
    graphe.py            graphe du monde : entités, arêtes typées, composantes, ponts, centralités, retrait de nœuds
    specification.py     spécification de décision typée (objectifs, contraintes dures/souples, politique de preuve, revue humaine)
    compilateur.py       intention en langage naturel → spécification (grammaire déterministe ; LLM optionnel, validé)
    optimisation.py      affectation par tours : MILP paramétrable, frontière de Pareto, sensibilité (solveur HiGHS)
    validation.py        échelle de validation L0-L8 avec validateurs indépendants du solveur
    critique.py          critique (objections structurées) et gardien (politique, consentement, divulgation)
    scenarios.py         base → intervention → delta ; contre-factuels ; test de stress ; rejeu ; branches
    execution.py         exécution de décision (Decision Run) : trace minutée réelle, instantanés hachés, persistance
    certificat.py        certificat généré depuis l'exécution
    modeles.py           passerelle de modèles : registre de capacités (configurées vs vérifiées), repli tracé
  adaptateurs/club/    SPÉCIFIQUE : profils, taxonomie, moteur de preuves existant → modèle canonique
  app/                 produit existant (inchangé) ; expose la plateforme par l'API et le MCP
```

Le jour du challenge : on écrit `adaptateurs/<challenge>/` (entités, objectifs, contraintes, outils) ; la plateforme ne change pas.

## 2. Boucle de décision (ce qui s'exécute réellement)

```
intention ─► compilateur ─► spécification ─► aperçu du plan ─► stratégie de contexte
   ─► adaptateur (affirmations + graphe) ─► opportunités (avec preuves et dette de preuve)
   ─► optimisation (Pareto) ─► validation L0..L6 ─► critique ─► gardien ─► médiation
   ─► certificat ─► revue humaine ─► (action : aperçu → autorisation → exécution → vérification)
```
Chaque étape écrit une entrée de trace (durée mesurée, entrées/sorties hachées).

## 3. Qui décide quoi

| Tâche | Composant | Jamais par |
|---|---|---|
| Comprendre l'intention | compilateur (règles ; LLM en option, sortie validée par schéma et vocabulaire fermé) | — |
| Contraintes dures, comptages, métriques de graphe, arithmétique de scénario | code déterministe | LLM |
| Optimisation | HiGHS (MILP), optimum prouvé ou statut explicite | LLM |
| Vérifier une solution | validateurs **indépendants** du solveur | le solveur lui-même |
| Objections | critique (règles déterministes ; LLM en option, marqué INFÉRÉ) | — |
| Politique, consentement, divulgation | gardien (règles) | LLM |
| Décider | humain | système |

Un agent peut répondre AGIR, S'ABSTENIR, DEMANDER PLUS DE PREUVES, ESCALADER. L'abstention est un résultat valide.

## 4. Statuts d'information (jamais convertis en silence)
VÉRIFIÉ · DÉCLARÉ · OBSERVÉ · INFÉRÉ · SYNTHÉTIQUE · SIMULÉ · PROPOSÉ · PÉRIMÉ · REJETÉ.
Une opportunité ne devient pas une recommandation de haute confiance tant que sa **dette de preuve** est matérielle.

## 5. Ce qui N'EST PAS construit maintenant, et pourquoi

| Élément | Décision | Raison |
|---|---|---|
| Microservices | Non : monolithe modulaire, frontières d'API internes typées | Aucune mise à l'échelle indépendante, isolation ou cycle de vie distinct n'est nécessaire aujourd'hui (MILP < 0,1 s) |
| Kubernetes | Non (P2) | Un seul conteneur suffit ; il deviendra utile pour des balayages de scénarios parallèles lourds, pas avant |
| Bus d'événements (NATS) | Non (P2) | Aucune charge asynchrone réelle ; les exécutions durent < 2 s |
| A2A | Non | Pas de cas d'usage mesuré au-delà de l'expérience des intentions scellées |
| OpenTelemetry | Différé ; trace structurée maison dans l'exécution | Même information (étapes, durées, versions) sans collecteur à opérer |
| Base de graphe | Non : graphe en mémoire (NetworkX) reconstruit depuis les affirmations | ≤ quelques milliers de nœuds |

## 6. Tranche verticale minimale (V1)
« Préparer la prochaine soirée du Club » comme exécution de décision complète :
intention en français → spécification validée → aperçu du plan → affirmations (DÉCLARÉ / SYNTHÉTIQUE) et graphe →
opportunités de rencontre avec preuves → frontière de Pareto (valeur / couverture / diversité sectorielle) →
validation indépendante → critique → gardien → certificat → rejeu (même empreinte) → contre-factuel (« et sans la
contrainte de langue ? ») → test de stress (retrait de N membres, réparation).

Critères d'acceptation mesurables : rejeu bit à bit identique ; 0 violation détectée par les validateurs indépendants ;
certificat entièrement dérivé des enregistrements ; chaque rencontre proposée rattachée à ≥ 1 affirmation DÉCLARÉE ;
abstention correcte quand la spécification est infaisable.
