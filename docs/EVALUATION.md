# Évaluation : définitions, jeux, résultats, limites

**Tout est exploratoire.** 37 profils fictifs (dont l'utilisatrice de démonstration et 1 visiteur). Les cas, la taxonomie et les profils
ont été écrits par le même auteur (Claude). Ces chiffres montrent que **le mécanisme fonctionne comme conçu** ; ils ne prouvent pas son
**utilité pour les membres du Club**, qui n'a jamais été testée.

Reproduire : `cd prototype && python -m eval.run_eval` (écrit `eval/resultats_{base,adversarial,reserve}.md`).

## Définitions (toutes mesurées sur le top 3, c'est-à-dire ce que l'utilisateur voit)

| Mesure | Définition | Dénominateur |
|---|---|---|
| **succès@3** | Au moins un profil « attendu » figure parmi les 3 premières suggestions | cas où une réponse existe (`abstention: false`) |
| **violations** | Au moins un profil « interdit » dans le top 3 : contrainte violée (zone, langue, consentement…), faux ami, visiteur ou membre refusant les introductions | tous les cas du jeu |
| **abstention correcte** | Le système s'abstient quand aucune bonne réponse n'existe, et seulement dans ce cas | tous les cas du jeu |
| **critères conformes** | Chaque critère attendu (type, valeur, obligatoire ou souhaité) est présent ; chaque critère interdit est absent | nombre total de critères vérifiés |
| **preuves vérifiées** | Chaque raison affichée se retrouve mot pour mot dans le champ cité du profil | nombre de preuves affichées |

**Référence** : recherche par mots-clés communs **avec exactement les mêmes filtres durs** (consentement, communauté, zone, langue,
concurrence). La comparaison isole la qualité du classement, pas celle des filtres.

## Trois jeux, trois statuts

| Jeu | Rédigé | Rôle | Statut |
|---|---|---|---|
| `cas.json` (20 cas) | Cycle 1 | Développement du cycle 1 | **Régression** : doit rester à 0 violation et 100 % d'abstentions correctes (vérifié par les tests) |
| `cas_adversariaux.json` (20 cas) | Lot 2, **avant** les corrections (commit `829e956`) | Mesure des fragilités signalées, puis **développement** | Premier résultat archivé (`eval/archives/v1_avant_lot2_*`) ; les résultats suivants sont des résultats **d'entraînement** |
| `cas_reserve.json` (14 cas) | Lot 2, **après** les corrections, formulations nouvelles | Estimation de généralisation **au lot 2** | Première exécution archivée (`v2_premiere_execution`). Depuis le lot 3 il est **post-hoc** : ses échecs ont inspiré des ajouts de vocabulaire (« gérer l'entrée », « épiceries fines ») |
| `cas_reserve2.json` (18 cas) | Lot 3, **avant** les améliorations de couverture (commit `59a4cee`) | Vérifier que les améliorations prévues (pluriels, allemand, paraphrases) fonctionnent | Exécuté une fois (`v3_premiere_execution`). **Fortement circulaire** : écrit en connaissant le vocabulaire qui allait être ajouté |

Aucun jeu n'est une **évaluation indépendante** : il faudrait des cas écrits par l'équipe, l'auditeur ou des membres, sans voir les profils.

## Résultats (analyse par règles, 28.09.2026)

| Jeu | Mesure | Le Fil du Club | Mots-clés + mêmes filtres |
|---|---|---|---|
| Base (régression) | succès@3 | 16/16 | 14/16 |
| | violations | **0/20** | 8/20 |
| | abstention correcte | 20/20 | 17/20 |
| Adversarial, **avant** corrections | critères conformes | 12/18 | — |
| | succès@3 | 10/13 | 12/13 |
| | violations | 2/20 | 6/20 |
| | abstention correcte | 17/20 | 15/20 |
| Adversarial, **après** corrections (entraînement) | critères conformes | 18/18 | — |
| | succès@3 | 13/13 | 12/13 |
| | violations | 0/20 | 5/20 |
| | abstention correcte | 20/20 | 16/20 |
| **Réservé** (une exécution) | succès@3 | **9/12** | 11/12 |
| | violations | **0/14** | 4/14 |
| | abstention correcte | **11/14** | 13/14 |

| **Lot 3 : réservé n°1 post-hoc** | succès@3 | 12/12 | 11/12 |
| | violations | 0/14 | 4/14 |
| | abstention correcte | 14/14 | 13/14 |
| **Lot 3 : réservé n°2** (une exécution, circulaire) | succès@3 | 15/15 | 7/15 |
| | violations | 0/18 | 0/18 |
| | abstention correcte | 18/18 | 14/18 |

Base et adversarial sont inchangés après le lot 3 (16/16, 0/20, 20/20 ; 13/13, 0/20, 20/20, 18/18 critères) : pas de régression.

**Le chiffre à citer au jury reste la première exécution du réservé n°1 (9/12, 0/14, 11/14)**, la seule mesure faite sans
connaître les cas. Les chiffres du lot 3 montrent que la couverture a progressé *sur des cas connus* ; une mesure indépendante manque toujours.

Preuves vérifiées : 41/41 (base), 47/47 (adversarial), 19/19 (réservé, lot 2). Ce résultat est **vrai par construction** avec des explications
extraites du profil : le garde-fou n'aura d'enjeu que si un LLM rédige un jour les explications.

Latence locale (médiane) : analyse ≈ 1 à 2 ms, recherche ≈ 8 à 15 ms pour 37 profils. Coût : nul (aucun appel externe).

### Lecture honnête
- Sur des formulations nouvelles, le moteur **ne propose jamais de mauvais contact** (0/14), mais il **se tait trop** : 3 fausses abstentions
  sur 14 (« des agents pour gérer l'entrée », « panneaux photovoltaïques » au pluriel, « épiceries fines zurichoises »).
- La référence trouve plus souvent (11/12), mais au prix de **4 violations sur 14** (un loueur de sites web pour des chariots élévateurs,
  un frigoriste pour du transport, etc.).
- Autrement dit, le moteur à règles est **précis mais fragile face au vocabulaire**. C'est précisément là qu'un LLM devrait apporter de la valeur
  (paraphrases, pluriels, allemand). Hypothèse **non mesurée** : aucune clé API disponible (voir plus bas).

## Décision « hors catalogue » (comparaison observée)

Sur le jeu adversarial, **sans** puis **avec** la recherche textuelle dans les offres déclarées (seuil : au moins 2 racines communes et au moins la moitié des racines du besoin) :

| Variante | succès@3 | violations | abstention correcte |
|---|---|---|---|
| Sans texte libre | 11/13 | 0/20 | 18/20 |
| Avec texte libre | 13/13 | 0/20 | 20/20 |

Aucune régression sur le jeu de base. **Retenu**, avec deux réserves : l'échantillon est de 4 cas pertinents, et le jeu réservé montre qu'un
seuil strict rate des paraphrases (« épiceries fines zurichoises »). Alternatives écartées pour l'instant : embeddings (aucun modèle
téléchargeable ici, et ils risquent de réintroduire les faux amis) ; mapping par LLM (non testable sans clé).

## Claude : ce qui est prêt, ce qui manque
- **Prêt** : `scripts/verifier_claude.py` exécute les 40 cas (base + adversarial) contre l'API réelle. Il mesure : critères conformes, succès, violations,
  abstention, latence (médiane et maximum), délai du premier critère affiché, jetons, coût estimé, taux de repli, accord avec les règles.
  Coût estimé : ≈ 0,56 USD (`claude-opus-5`, estimation grossière). Rien n'est exécuté sans `--confirmer`.
- **Testé** : uniquement avec un client simulé (flux découpé, refus, JSON invalide, panne). Le schéma de sortie structurée n'a **jamais**
  été soumis à l'API réelle : un rejet du schéma par l'API est possible et serait visible (repli affiché).
- **Manque** : une clé `ANTHROPIC_API_KEY` dans l'environnement d'exécution. Aucune dépense n'a été engagée.

## Améliorations de couverture du lot 3
- **Pluriels et singuliers générés automatiquement** pour chaque expression (« audit énergétique » → « audits énergétiques ») : 760 formes, aucune collision entre concepts (vérifié).
- **Allemand** : compétences (Treuhand, Übersetzer, Kühltransport…), verbes de recherche (suche, brauche), lieux (Wallis, Zürich, Bern…), langues.
- **Paraphrases** : vigiles, contrôle d'accès, épiceries fines, loueur…
- **Faux ami retiré** : « données » seul ne signifie plus « Données et IA » (« protéger nos données clients »).

## Tests automatisés (`python -m pytest -q tests`, 22 tests)
Ils couvrent les risques, pas le volume : invariants de consentement ; symétrie Bourse ⇔ correspondances ; cascades (retrait du consentement,
clôture, modification) ; machine à états et rôles ; anonymat levé seulement après acceptation ; sollicitation limitée aux membres qui correspondent ;
mode réel sans simulation ni journal exposé ; critères inventés refusés par le serveur ; flux Claude (provisoire filtré au final, repli sur panne, refus ou JSON invalide) ; non-régression base et adversarial.
Le parcours navigateur (`scripts/parcours_demo.py`) sert de test de bout en bout.
