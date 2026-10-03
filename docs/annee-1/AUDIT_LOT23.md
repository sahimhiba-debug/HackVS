# Audit des lots 2 (comptes) et 3 (espace membre) — constats et suites

> **Construit — branche `annee-1`, pas dans la démo.** Audit d'un sous-agent à contexte neuf, en lecture seule, sur
> `c6c6f4a`. Chaque constat corrigé a d'abord un test ROUGE (`prototype/tests/test_annee1_audit_lot23.py`), puis vert.

L'audit a vérifié **sans rien trouver** : aucun XSS (`textContent` partout), comparaisons HMAC en temps constant, aucun
jeton ni secret en clair dans le journal, contrôle d'origine (CSRF), et — interrupteurs éteints — **la démo est
identique** à celle d'avant les lots (même empreinte du journal et de l'état, mêmes demandes, mêmes découvertes).

| Constat | Gravité | Suite |
|---|---|---|
| B1 — après une suppression, offres, capacités et protocoles ne se lisaient plus (dates et heures remplacées par « [effacé] ») ; 500 sur plusieurs routes, même après redémarrage | BLOQUANT | **corrigé** : la purge ne touche que des TEXTES (repérés par leur forme), jamais une date, une heure ou un identifiant ; le monde purgé est rejoué et relu dans une copie AVANT toute écriture (offres, protocoles, capacités, état complet). Testé sur la scène jouée en entier, pour trois membres |
| B2 — deux suppressions le même jour : trace PURGE identique, réécriture refusée, suppression à moitié | BLOQUANT | **corrigé** : trace unique (aléa) ; la purge est faite AVANT l'effacement — si elle échoue, rien n'est effacé ; si l'effacement échoue après, recommencer est sans danger |
| B3 — la pause ne bloquait que les essais (demandes, découvertes, boîte de sortie continuaient) | BLOQUANT | **corrigé** : `sollicitable()` (donc demandes et e-mails), détection et observation (le membre en pause y est indisponible), découvertes qui demanderaient son accord écartées |
| B4 — le second facteur se remplaçait avec la seule session | BLOQUANT | **corrigé** : un second facteur ACTIF ne se remplace que depuis une session élevée par un code de l'ancien ; le remplacement est journalisé |
| I1 — inviter, changer un rôle, révoquer : sans second facteur ; le dernier administrateur pouvait se révoquer | IMPORTANT | **corrigé** : ces actions exigent la console (TOTP + session élevée) ; jamais sans administration |
| I2 — CLAIMS 106 disait la console « réservée aux comptes nominatifs » ; la console de la DÉMO garde son jeton | IMPORTANT | **corrigé dans CLAIMS** : les comptes nominatifs gardent la console du secrétariat (lot 4) ; la console de la démo reste au jeton |
| I3 — des textes du membre restaient recopiés chez d'autres (adaptations, protocoles, accords) | IMPORTANT | **corrigé** : chaque texte est remplacé PARTOUT où il a été recopié, plus le nom, le courriel et le téléphone. Limite : un texte d'un seul mot en minuscules (« tisanes ») ressemble à un identifiant et reste |
| I4 — sur le disque : PostgreSQL gardait l'ancienne version de la ligne ; SQLite dépendait de sa compilation | IMPORTANT | **corrigé** : `PRAGMA secure_delete = ON` ; `VACUUM FULL` après une purge sous PostgreSQL (test : le texte est dans le fichier avant, absent après — et le test échoue sans le correctif). Le WAL de PostgreSQL garde l'ancienne version le temps de sa rétention : à régler en production |
| I5 — un autre objet sur le même journal gardait le texte en mémoire | IMPORTANT | **corrigé** : compteur de réécritures dans la base, lu avec la signature du journal (même requête) |
| I6 — export sans identité ni contenu des notes | IMPORTANT | **corrigé** : identité du coffre et notes privées ajoutées (format v2). Essais et reçus détaillés : à compléter |
| I7 — effacement et purge non atomiques | IMPORTANT | **corrigé** avec B2 (ordre purge → effacement → seconde passe) |
| M1 — en démo SQLite, « Nouvelle démonstration » efface aussi les comptes | MINEUR | noté (la démo est un bac à sable ; refusé sur PostgreSQL depuis l'audit du lot 1) |
| M2 — pas de blocage après des codes TOTP faux (seule la limite par session) | MINEUR | **non fait** |
| M3 — préférences stockées sans effet | MINEUR | **corrigé par le lot 5** : les notifications suivent langue et canaux |
| M4 — coût du crochet de pause | MINEUR | mesuré par l'audit, accepté (cache par version du journal) |
| M5 — la session restait dans l'adresse de `/espace` | MINEUR | **corrigé** : elle passe dans le stockage de session et quitte l'adresse |
