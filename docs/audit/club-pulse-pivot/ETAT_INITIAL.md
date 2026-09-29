# État initial avant le pivot (2026-09-29, commit `cbb6930`)

Établi en lisant le code et en exécutant les contrôles, pas les anciens rapports. Arbre de travail propre, branche
`claude/modest-bohr-xvk53n`, tout poussé ; `make quality-check` vert (438 tests + 5 de bout en bout, lint, types).

## Ce qui fonctionne réellement
- **Journal d'événements** (`plateforme/memoire.py`) : SQLite en ajout seul, transactions tout-ou-rien, idempotence par
  empreinte du contenu, rejeu. Fiable, testé.
- **Accès** : codes d'invitation (HMAC) → session signée (HMAC-SHA256, expiration 12 h), secret obligatoire ou aléatoire ;
  compte effacé → session refusée. Pas de cookie (en-tête `X-Pulse-Session`, `sessionStorage`) ⇒ pas de CSRF membre.
- **Coffre d'identités** + pseudonymes + rendu par spectateur ; erreurs typées → HTTP à un endroit ; un verrou par monde.
- **Frontière IA** : `Intelligence` unique, Apertus (client HTTP compatible OpenAI) ou repli déterministe déclaré,
  sorties validées, disjoncteur. **Apertus jamais appelé** : aucun identifiant dans l'environnement.
- **PWA** `/app` et **console** `/console` (CSP par empreintes, protections HTTP, journaux sans contenu privé).
- **Moteur d'activation** (machine d'états, accords privés, replanification) — mais nourri par un **scan général du réseau**.

## Ce qui manque pour la direction demandée
- Aucune **offre volontaire** (ce qu'une personne accepte de fournir, ses conditions, sa période, sa capacité) : le moteur
  déduit des « capacités » des profils — une compétence passée traitée comme une disponibilité.
- Aucun **protocole versionné** ni **accord lié à une portée et à une version** : un accord porte sur une étape, sans
  empreinte de ce qui a été accepté ; une modification ne sait pas quels accords restent valables.
- Aucune **observation** avec portée, auteur, contestation ; aucun **droit de réutilisation** distinct de la mémoire.

## Ce qui est trop large
Scan de tout le réseau (8 familles d'opportunités), fil « Pouls » d'opportunités générées, tour de contrôle avec
indicateurs du réseau, graphe avant/après, 10 étapes de démonstration autour d'une recherche de traducteur, ancien
prototype « Le Fil du Club » (10 pages) toujours servi.

## Ce qui est fragile
- État des membres (notes, préférences, coffre, sessions) en mémoire du processus ; monde recréé à chaque réinitialisation.
- La démonstration repose sur des gestes « joués » par la console dans UN téléphone intégré, pas sur deux comptes.

## Ce qui sera réutilisé
Journal + transactions, coffre, sessions, erreurs typées, `au_monde` (un monde, un verrou), `Intelligence` (nouvelle tâche
« structurer un essai » avec secours formulaire), PWA et console (réécrites sur le nouveau parcours), protections HTTP,
observabilité, CI.

## Ce qui sort du parcours visible (sans suppression hâtive de code)
Fil d'opportunités, scan et tour de contrôle du réseau, graphe d'évolution, démonstration guidée en 10 étapes, onglets
Pouls / Activations / Événements. Leurs routes API restent protégées et testées ; elles ne sont plus liées depuis
l'application ni la console. L'ancien prototype reste servi (autres données, autres sessions : ne touche pas la tranche).

## Scénario choisi : banc d'essai partagé (illustratif, FICTIF)
Sophie (exposante fictive, tisanes) veut savoir si sa nouvelle étiquette est comprise en 10 secondes à 1 mètre par
quelqu'un qui ne connaît pas la marque. Markus a publié une offre : « 15 minutes de regard neuf sur un emballage » ;
Pauline : « un présentoir éclairé sur mon stand ». Proposition préparée → Sophie confirme le critère → Markus accepte sa
part → **perturbation : Markus n'a plus que 5 minutes** → le système invalide son accord, préserve celui de Pauline,
propose « remplacer par Léa » ou « raccourcir le geste » (ou s'arrête) → nouvelles décisions → essai réalisé →
observation déclarée par Sophie, avec ses limites, confirmable ou contestable → droits de réutilisation choisis.
**Aucune demande réelle d'exposant n'existe dans les documents fournis** : le scénario est illustratif et affiché comme tel.
Plan B conservé : « le bon retour » (même primitives), non construit tant que le banc d'essai tient.
