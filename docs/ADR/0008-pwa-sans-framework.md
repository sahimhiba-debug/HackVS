# ADR 0008 — Application du membre : PWA sans framework ni étape de construction

Statut : **accepté** (prototype). Date : 2026-09-29.

## Contexte
Démonstration sur téléphone, une équipe réduite, aucun temps pour une chaîne de construction front.

## Décision
`web/pulse/app.html` et `console.html` : JavaScript natif (modules en ligne), DOM construit par `createTextNode`
(jamais `innerHTML`), routeur par ancre, `sessionStorage` pour la session, service worker qui met en cache
l'enveloppe seulement (les DONNÉES jamais : elles sont personnelles et doivent rester à jour). CSP stricte : scripts
autorisés par empreinte SHA-256 calculée au démarrage — ni `unsafe-inline` ni `unsafe-eval`.
Chaque navigation ouvre une génération : une réponse d'un écran quitté n'est jamais affichée ; délai de 15 s ;
écran d'erreur avec « Réessayer » et référence de requête ; hors ligne dit comme tel.

## Conséquences
+ Aucune dépendance front, aucun paquet npm à auditer ; testé dans un vrai navigateur (390×844, 412×915, pannes réseau).
− Deux fichiers HTML volumineux ; pas de typage du code front. Au-delà du prototype : TypeScript + composants.
− Styles en ligne permis par la CSP (risque faible, documenté).
