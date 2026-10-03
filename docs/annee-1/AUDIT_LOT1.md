# Audit du lot 1 — constats et suites

> **Construit — branche `annee-1`, pas dans la démo.** Audit fait par un sous-agent à contexte neuf sur
> `cd4c448..82d0a6a` (rien de modifié par lui). Chaque correctif a d'abord un test ROUGE, puis vert, dans
> `prototype/tests/test_annee1_stockage.py` ou `test_annee1_exploitation.py` (préfixe `test_b1_`, `test_i3_`, …).

Ce que l'audit a vérifié et trouvé SANS problème : sous SQLite, aucune divergence entre l'ancien et le nouveau journal
sur 600 scénarios aléatoires (la démo n'est pas touchée) ; 343 tests ClubPulse avec le journal sur PostgreSQL.

| Constat | Gravité | Suite |
|---|---|---|
| B1 — `splitlines()` coupait sur U+2028, U+0085… : sauvegarde « réussie » mais illisible | BLOQUANT | **corrigé** : coupe sur « \n » seulement ; la sauvegarde est relue avant d'être mise sous son nom ; le provisoire est supprimé en cas d'échec ; `fsync` |
| B2 — PostgreSQL : connexion perdue pour toujours ; l'annulation levait et sautait F27 | BLOQUANT | **corrigé** : reconnexion hors transaction (requête rejouée une fois, toutes idempotentes) ; l'annulation ne lève jamais ; cache et abonnés F27 remis à zéro même si la validation échoue |
| I1 — l'empreinte ne couvrait pas `statut` (SIMULE → VERIFIE accepté) | IMPORTANT | **corrigé** : format v2, empreinte SHA-256 de chaque ligne entière |
| I2 — restauration validée PUIS refusée (doublon) | IMPORTANT | **corrigé** : doublons refusés à la lecture ; vérification relue DANS la transaction, avant validation ; « cible vide » contrôlé sous le même verrou |
| I3 — `seq` renumérotés à la restauration (références des reçus) | IMPORTANT | **corrigé** : `seq` sauvegardé et restauré tel quel ; la séquence repart après le plus grand (PostgreSQL : `setval`) |
| I4 — migrations concurrentes sur PostgreSQL (UniqueViolation) | IMPORTANT | **corrigé** : verrou consultatif `pg_advisory_lock`, niveau relu sous le verrou |
| I5 — DDL SQLite hors transaction (journal supprimé, niveau inchangé) | IMPORTANT | **corrigé** : `BEGIN` explicite ; un pas qui échoue ne laisse rien à moitié |
| I6 — « Nouvelle démonstration » vidait le journal PostgreSQL | IMPORTANT | **corrigé** : refusé (409) quand le journal est sur PostgreSQL. Reste : pas de service de sauvegarde planifiée dans le compose |
| I7 — variables lues mais non documentées (dont `OPENAI_API_KEY`, secret) | IMPORTANT | **corrigé** : 15 variables ajoutées ; la découverte du test couvre `env.get`, les chaînes de forme `HACKVS_…` et les noms composés `<PREFIXE>_DELAI_S` |
| I8 — le test « reprend son journal » passait aussi après un réensemencement | IMPORTANT | **corrigé** : un fait témoin doit survivre au redémarrage |
| M1 — `vider()` en transaction : comportements différents | MINEUR | **corrigé** : refusé partout |
| M2 — `executer` remplaçait `?` naïvement | MINEUR | **corrigé** : SQL sans paramètre envoyé tel quel ; `%` doublé avec paramètres |
| M3 — adresse fautive → sauvegarde vide « valide » ; `migrer … 1x` accepté ; sauvegarder migrait | MINEUR | **corrigé** : adresse sans journal refusée ; niveau illisible refusé ; la sauvegarde lit sans migrer |
| M4 — `/sante/pret` publique donnait le nombre de faits et attendait le verrou | MINEUR | **corrigé** : plus le nombre de faits ; verrou attendu 2 s au plus (sinon 503) |
| M5 — `/metriques` hors machine seulement avec le jeton de console (jeton d'administration) | MINEUR | **non fait** : jeton dédié `HACKVS_METRIQUES_JETON` à prévoir |
| M6 — compose : superutilisateur PostgreSQL, mot de passe en variable, psycopg non épinglé, image jamais construite | MINEUR | **en partie** : psycopg épinglé dans `constraints.txt`. Rôle applicatif dédié et secret Docker : à faire. Image : pas de démon Docker dans cette session |
| M7 — vitrine du lot 1 : commande et sortie ne concordaient pas | MINEUR | **corrigé** : sorties refaites pour de vrai après les correctifs |
| M8 — divers (`lire` charge tout en mémoire, `chiffres_demo()` inutilisé, titres « annee1 » dans le JSON public de la feuille de route) | MINEUR | **non fait**, noté |
| Note lot 3 — `reecrire` dans une transaction | — | **corrigé** : refusé. La purge n'atteint pas les sauvegardes déjà faites : la rétention des sauvegardes est à fixer (lot 6) |

Le conteneur « unhealthy » n'est pas redémarré par `restart: unless-stopped` : avec la reconnexion (B2), une coupure de
PostgreSQL ne laisse plus le processus en panne ; un superviseur qui relance sur « unhealthy » reste à prévoir.
