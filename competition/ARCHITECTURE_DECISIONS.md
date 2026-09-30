> ⛔ **OBSOLÈTE — produit d'avant le pivot, ne pas présenter.** Ce dossier décrit l'ancien produit (« intelligence relationnelle »), pas le registre des capacités. La réécriture du pitch est en cours (équipe) ; voir `TODO-DEMO.md`.

# Décisions d'architecture (défendables devant un jury technique)

Format : PROBLÈME · OPTIONS · CHOIX · POURQUOI · COMPROMIS · RÉSULTAT. Chaque résultat renvoie à une preuve exécutable.

## AD-01 — Graphe temporel : un journal de faits datés, pas une table « A connaît B »
- **Problème.** « A connaît B » ne dit ni quand, ni pourquoi, ni ce qui a suivi : impossible de savoir qu'une relation
  s'éteint ou qu'un suivi est dû.
- **Options.** Table de relations ; base de graphe (Neo4j) ; journal d'événements en ajout seul + graphe dérivé.
- **Choix.** Journal en ajout seul (`plateforme/memoire.py`), événements immuables, graphe dérivé à la lecture (NetworkX).
- **Pourquoi.** Tout est rejouable et auditable ; l'état d'une relation (rencontrée, à raviver, opportunité) est une
  fonction des faits, calculée par UNE règle (`reseau._etat`).
- **Compromis.** Recalcul à la lecture ; SQLite mono-processus ; pas de requêtes graphe persistées.
- **Résultat.** Scène rejouée à l'identique (`test_scene.py::test_rejeu_identique_trois_fois`) ; « actuel » = moins de
  90 jours, une hypothèse de produit déclarée.

## AD-02 — Une seule source de vérité par donnée
- **Problème.** Les introductions vivent dans le magasin (workflow, permissions), les rencontres dans la mémoire.
  Deux listes = divergence ou double compte (FAILURES n° 1, 3, 42).
- **Options.** Tout migrer ; dupliquer à l'écriture ; projeter le magasin dans la mémoire.
- **Choix.** Le magasin reste propriétaire de son workflow ; ses transitions sont PROJETÉES (idempotent) ; les lecteurs
  passent par une fonction unique (`cycle.besoins_actifs`).
- **Pourquoi.** Aucune écriture en double ; réinitialiser vide les deux.
- **Compromis.** Une projection à chaque lecture.
- **Résultat.** Le besoin compté deux fois (n° 42) a disparu ; test de la tour de contrôle.

## AD-03 — Compilateur d'intention déterministe (règles + taxonomie), l'IA générative en option contrôlée
- **Problème.** Comprendre « un partenaire pour l'Allemagne, qui connaît la distribution, pas un concurrent, en
  français » sans dépendre d'un service externe, et sans deviner.
- **Options.** LLM seul ; embeddings seuls ; règles sur un vocabulaire fermé + termes ambigus résolus par indices.
- **Choix.** Règles et taxonomie (`app/parser_rules.py`, `data/taxonomie.json`) : chaque critère cite l'extrait qui le
  justifie ; un terme ambigu n'est résolu que si un seul sens a des indices (ou est déjà exprimé), sinon il devient une
  incertitude explicite.
- **Pourquoi.** Reproductible, hors ligne, explicable ; l'erreur est visible (extrait) et testable.
- **Compromis.** Vocabulaire fermé : échoue sur les paraphrases très libres (22 échecs sur 112 cas) — c'est là que
  l'IA générative doit prouver sa valeur (banc G1, non exécuté faute de modèle).
- **Résultat.** Phrase du scénario et 4 variantes comprises ; contre-cas ambigus ; 112 cas inchangés
  (`test_compilateur_besoin.py`).

## AD-04 — Preuve avant proposition
- **Problème.** Une recommandation par ressemblance propose des gens « comme vous », pas des gens qui peuvent aider.
- **Options.** Similarité de profil ; score appris ; aide PROUVÉE (un besoin publié couvert par une offre déclarée).
- **Choix.** Aide prouvée : chaque proposition porte l'extrait exact qui la justifie (déclaré ou déduit, dit comme tel).
- **Pourquoi.** L'explication EST la décision (test de mutation) ; aucune donnée d'apprentissage nécessaire.
- **Compromis.** Sans besoin publié, pas de proposition : le démarrage dépend de ce que les membres écrivent.
- **Résultat.** Scène : Markus (preuve + réciprocité) ; Chantal : 15 introductions possibles, 0 fondée, un moteur par
  ressemblance aurait proposé quelqu'un (C23).

## AD-05 — Optimiseur pour les décisions collectives, simple tri pour la recherche individuelle
- **Problème.** Classer « les meilleurs pour A » envoie tout le monde vers les mêmes personnes et ignore le réseau.
- **Options.** Tri par score ; glouton ; programme linéaire en nombres entiers (HiGHS) ; front de plans.
- **Choix.** MILP pour les soirées (optimum prouvé), front de plans approché (glouton pondéré + heuristiques) pour les
  introductions du mois ; l'humain choisit.
- **Pourquoi.** Le réseau a plusieurs objectifs en conflit (inclusion, cohésion, robustesse, réciprocité) : montrer le
  prix de chaque choix plutôt qu'un score unique.
- **Compromis.** Front approché, pas exhaustif ; perd sur la réciprocité face à une méthode dédiée (SYNTHETIC_BENCHMARK).
- **Résultat.** Scène : groupes 2 → 1, groupe robuste 4 → 15 ; gains mémorisés par état : 500 membres de 11,2 s à
  6,8 s, résultats identiques à l'octet (FAILURES n° 46).

## AD-06 — L'abstention est un résultat de première classe
- **Problème.** Un système qui répond toujours finit par recommander n'importe qui — et par gonfler ses indicateurs.
- **Options.** Toujours proposer le meilleur candidat ; seuil de score ; s'abstenir sans preuve et le dire.
- **Choix.** S'abstenir (recherche, relance, introduction, soirée), avec la raison objective et ce qui changerait la
  décision.
- **Pourquoi.** La confiance d'un réseau humain se perd en une mauvaise introduction.
- **Compromis.** Le système paraît souvent silencieux (dit dans le pitch).
- **Résultat.** 17 silences pour 1 relance ; 9 → 1 → 0 rencontres utiles puis abstention (C24) ; Japon (C01).

## AD-07 — Confidentialité par construction, y compris par inférence
- **Problème.** Un compte, une couleur de graphe ou un message d'erreur peuvent révéler qui refuse ou qui connaît qui.
- **Options.** Politique écrite ; contrôle d'accès seul ; règles testées contre l'inférence.
- **Choix.** Invisible par défaut ; k-anonymat 3 sur les écartés ; chemin d'un tiers jamais révélé ; 409 uniforme ;
  aucune coordonnée avant double accord ; entrées bornées.
- **Compromis.** Moins d'information affichée (« ni nommé, ni compté »).
- **Résultat.** Tests `test_scene.py`, `test_securite_api.py`, `test_adversarial_sprint.py` ; FAILURES n° 19, 21, 22.

## AD-08 — Double accord ; un refus n'est jamais contourné
- **Problème.** Un optimiseur valide mathématiquement peut placer à la même table deux personnes dont l'une a refusé.
- **Choix.** Introduction proposée, acceptée ou refusée ; le refus est une contrainte NON levable, revérifiée par un
  validateur indépendant et par le gardien.
- **Compromis.** Moins de rencontres possibles.
- **Résultat.** Équivalence `refus_motives` ⇔ `candidates` vérifiée sur toutes les paires ; FAILURES n° 26, 30, 36, 37.

## AD-09 — Passerelle de modèles : annoncé, configuré, vérifié — jamais confondus
- **Problème.** Dire « notre IA » sans l'avoir mesurée ; dépendre d'une clé le jour de la démo.
- **Options.** Appeler un LLM directement ; passerelle avec états et repli.
- **Choix.** `plateforme/modeles.py` : DOCUMENTÉE / CONFIGURÉE / VÉRIFIÉE ; sans fournisseur, repli déterministe
  jamais présenté comme une inférence ; le LLM propose des critères, le code les revalide ; il ne décide jamais.
- **Compromis.** Pas d'IA générative dans la démo (aucun modèle accessible) : dit tel quel.
- **Résultat.** C14 ; bancs G1/G2 prêts (moteur seul / IA seule / hybride / hybride économe), critères écrits avant.

## AD-10 — Plan d'action : rien ne part sans décision humaine, et rien de réel en démo
- **Problème.** Une recommandation qui s'exécute seule envoie des messages que personne n'a validés.
- **Choix.** Décision humaine → aperçu à blanc → exécution SIMULÉE en démo → vérification → empreintes
  (`plateforme/action.py`).
- **Compromis.** Aucun envoi réel implémenté (limite déclarée).
- **Résultat.** Une soirée n'entre en mémoire que depuis un plan approuvé (`cycle.enregistrer_soiree`).

## AD-11 — Simulation explicite, jamais confondue avec l'observation
- **Problème.** « Le réseau irait mieux » est invérifiable si l'on ne sépare pas le simulé du constaté.
- **Choix.** Toute projection est calculée sur une COPIE du graphe et étiquetée SIMULATION ; les faits réels sont
  comptés à part (échelle d'impact, boucle prévu / réalisé).
- **Compromis.** Hypothèses affichées (introductions supposées acceptées).
- **Résultat.** `test_scene.py::test_les_simulations_n_ecrivent_rien` ; contrefactuel « si cette relation disparaît ».

## AD-12 — Scène de démonstration : monde isolé qui réutilise le moteur
- **Problème.** Une démo scriptée ment ; une démo sur l'application complète est fragile.
- **Choix.** Monde fictif isolé, horloge simulée, étapes rejouables, MÊMES fonctions que l'application ; aucune règle
  propre à la page.
- **Résultat.** Rejeu déterministe ; bout en bout dans un vrai navigateur (bureau + mobile) en CI.

## AD-13 — Pas de « 10 agents », MCP seulement comme frontière
- **Problème.** Multiplier les agents rend la décision inauditable.
- **Choix.** Un moteur déterministe ; MCP expose ses outils à d'autres systèmes (frontière d'interopérabilité).
- **Résultat.** Serveur MCP testé (stdio et HTTP) ; hors démo.
