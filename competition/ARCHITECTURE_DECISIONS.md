# Décisions d'architecture (défendables devant un jury technique)

Format : PROBLÈME · OPTIONS · CHOIX · JUSTIFICATION · COMPROMIS · CONSÉQUENCE.

## AD-01 — Un graphe TEMPOREL plutôt qu'une table « A connaît B »
- **Problème.** « A connaît B » ne dit ni quand, ni pourquoi, ni ce qui s'est passé ensuite ; impossible de savoir
  qu'une relation s'éteint ou qu'un suivi est dû.
- **Options.** A : table de relations. B : base de graphe (Neo4j…). C : journal d'événements en ajout seul + graphe dérivé.
- **Choix.** C (`plateforme/memoire.py`).
- **Justification.** Chaque fait a une date, une source, un statut ; l'état (rencontrée, suivi en attente, à raviver)
  est recalculé, donc rejouable et auditable. 16 à 150 membres : NetworkX en mémoire suffit.
- **Compromis.** Recalcul à chaque lecture (négligeable à cette taille) ; pas de requêtes graphe complexes persistées.
- **Conséquence.** Les relances, la mémoire relationnelle et la simulation lisent la même vérité.

## AD-02 — Une seule source de vérité par fait (projection, pas fusion)
- **Problème.** Les introductions vivaient dans le magasin, les soirées dans la mémoire (défaut FAILURES #1).
- **Options.** A : tout migrer dans la mémoire. B : dupliquer à l'écriture. C : le magasin reste propriétaire de son
  workflow et de ses permissions ; ses transitions sont PROJETÉES dans la mémoire (idempotent).
- **Choix.** C. **Compromis** : projection à chaque lecture. **Conséquence** : aucune écriture en double ; réinitialiser
  vide les deux.

## AD-03 — Un solveur (programme linéaire en nombres entiers) plutôt qu'un classement
- **Problème.** Classer « les meilleurs pour A » ignore les autres membres : les mêmes personnes populaires sont
  recommandées à tous, et personne ne regarde le réseau entier.
- **Options.** A : tri par score. B : glouton. C : optimisation sous contraintes (HiGHS) de la valeur COLLECTIVE.
- **Choix.** C pour les décisions collectives (soirée, lot d'introductions) ; tri simple pour la recherche individuelle.
- **Justification mesurée.** SYNTHETIC_BENCHMARK : plus de membres servis, plus de ponts, moins d'isolés à budget égal ;
  optimum PROUVÉ. **Compromis** : 0,4 s au lieu de < 1 ms ; perd sur la réciprocité face à une baseline dédiée.

## AD-04 — Politique, permissions et contraintes DÉTERMINISTES ; le LLM seulement pour le langage
- **Problème.** Un modèle de langage peut halluciner, être manipulé par injection, et n'est pas auditable.
- **Choix.** Le consentement, la confidentialité, les contraintes, la validation et l'autorisation d'action sont du code
  testé. L'IA (règles locales, IA locale e5, Claude/Apertus en option) propose ; le code revalide chaque critère.
- **Conséquence.** Même sans aucune clé d'API, le produit fonctionne entièrement ; une réponse de LLM ne peut pas lever
  une règle du gardien.

## AD-05 — L'abstention est un résultat
- **Problème.** Un système de recommandation qui répond toujours finit par recommander n'importe qui.
- **Choix.** S'abstenir, demander plus de preuves ou escalader vers l'humain sont des décisions de première classe
  (scénarios S03, S08, S09 ; « Japon » en scène ; 17 paires sans relance).
- **Compromis.** Moins de propositions ; c'est voulu.

## AD-06 — Introduction en DOUBLE ACCORD, jamais de coordonnées
- **Problème.** « Voici le numéro de Marc » viole la confidentialité et la confiance du Club (dont l'annuaire ne
  communique pas publiquement les contacts, selon le brief).
- **Choix.** Demande → la personne sollicitée accepte ou refuse → coordonnées partagées seulement après. Le prototype ne
  stocke aucune coordonnée. Présentation par un tiers : proposée d'abord au tiers (AD-02, FAILURES #2).

## AD-07 — Relancer seulement avec une raison NOUVELLE et prouvée
- **Problème.** Les relances génériques (« restez en contact ») créent de la fatigue et du bruit.
- **Choix.** Raisons admises : besoin publié depuis la rencontre + offre citée ; autre sens de la réciprocité non servi ;
  présentation via un contact suivi. Sinon : silence, compté et affiché.

## AD-08 — MCP comme frontière d'interopérabilité, pas comme bus interne
- **Choix.** Serveur MCP pour les assistants externes (jetons, portées, confirmation humaine) ; l'intérieur reste des
  appels de fonctions. **Pourquoi** : une seule instance, aucun besoin de découplage asynchrone ; un bus ajouterait de
  la latence et des modes de panne sans bénéfice mesurable.

## AD-09 — Pas de « 10 agents »
- **Choix.** Des rôles à responsabilité démontrable (compilateur d'intention, solveur, validateurs, critique, gardien,
  médiateur), déterministes quand c'est possible. Aucun agent n'existe pour faire joli.

## AD-10 — Mode scène : monde isolé qui réutilise le moteur
- **Options.** A : piloter la démo principale (état partagé, fragile). B : second serveur (duplication).
  C : monde isolé en mémoire, jeu de données fictif lisible, horloge fixe, MÊMES fonctions.
- **Choix.** C. **Conséquence** : rejouable à l'identique (testé 3 fois), rafraîchissement sûr, aucun code de démo
  « truqué » : chaque chiffre affiché est calculé.

## AD-11 — Vocabulaire fermé (taxonomie) + IA locale en suggestion, plutôt que des embeddings seuls
- **Problème.** Des embeddings seuls rapprochent « droit maritime » et « droit des sociétés » ; impossible de citer une preuve.
- **Choix.** Concepts contrôlés, preuves citées mot pour mot ; l'IA locale (multilingual-e5, ONNX, CPU) ne fait que
  PROPOSER des compétences quand les règles échouent, et le membre confirme.
- **Compromis.** Il faut enrichir le vocabulaire (ex. « Allemagne » ajouté ; évaluations relancées sans régression).

## AD-12 — Micro-cercle : glouton explicable plutôt qu'un solveur
- **Choix.** À cette taille (3 à 5 personnes), un glouton déterministe dont chaque ajout s'explique (« apporte 2 aides
  prouvées au groupe ») vaut mieux qu'un optimum opaque. C'est une PROPOSITION : chaque membre accepte.
