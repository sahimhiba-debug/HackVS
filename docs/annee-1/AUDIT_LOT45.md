# Audit des lots 4 (secrétariat) et 5 (notifications) — constats et suites

> **Construit — branche `annee-1`, pas dans la démo.** Audit d'un sous-agent à contexte neuf, en lecture seule, sur
> `d40fa0c`. Chaque constat corrigé a d'abord un test ROUGE (`prototype/tests/test_annee1_audit_lot45.py`), puis vert.

Vérifié **sans rien trouver** : aucun contournement de la garde du secrétariat (compte nominatif, TOTP, élévation),
aucun XSS, aucune SSRF par l'impression PDF (HTML entièrement échappé, aucune donnée de membre), exceptions SMTP
courantes attrapées, pause / désinscription / canaux respectés, gel des critères. Interrupteurs éteints : **même
journal et même état que la démo d'avant les lots** ; seul l'en-tête CSP des pages gagne deux empreintes de scripts
(ceux des nouvelles pages) — sans effet sur ce que les pages de la démo peuvent faire.

| Constat | Gravité | Suite |
|---|---|---|
| B1 — l'envoi SMTP se faisait sous le verrou du monde : un serveur SMTP muet gelait tout le Club (59,5 s d'attente mesurées) | BLOQUANT | **corrigé** : préparer (verrou) → expédier (SANS verrou) → tracer (verrou) ; délai SMTP réglable (`SMTP_DELAI_S`) ; test : une lecture répond pendant une relance vers un serveur muet |
| I1 — un retour à la ligne dans une adresse : erreur 500, relance interrompue, échec non suivi ; une virgule : deux destinataires | IMPORTANT | **corrigé** : une seule adresse sans retour à la ligne, sinon « échec — adresse invalide » ; toute erreur d'envoi est un échec suivi, jamais une relance cassée |
| I2 — chaque relance renvoyait tout | IMPORTANT | **corrigé** : un même modèle, un même canal, une fois par jour au plus (« déjà envoyé aujourd'hui ») |
| I3 — une campagne de 50 passes tenait le verrou ~5 s, sans plafond | IMPORTANT | **corrigé** : 20 invitations par campagne, 100 par jour |
| I4 — 300 liens faux bloquaient la désinscription de tout le monde | IMPORTANT | **corrigé** : signature vérifiée d'abord ; seuls les liens FAUX partagent un plafond ; un vrai lien a le sien |
| I5 — métiers à confirmer comptés en lignes, libellés rares montrés (un nom peut s'y cacher) | IMPORTANT | **corrigé** : comptés en ENTREPRISES distinctes (empreinte du nom, jamais rendue) ; un libellé porté par moins de 3 entreprises n'est jamais montré — seul leur nombre ; le secrétariat peut en saisir un pour le rattacher |
| I6 — un seuil non numérique rendait « atteint » vrai ou faisait planter la page ; mesure inconnue acceptée | IMPORTANT | **corrigé** : seuil numérique exigé, mesure vérifiée ; on ne gèle que des critères mesurables |
| M1 — lien STOP du SMS coupé par la troncature | MINEUR | **corrigé** : le corps est coupé, jamais le lien (480 caractères au plus) |
| M2 — repli vers le français non tracé | MINEUR | **corrigé** : raison « repli fr » |
| M3 — identifiant de membre avec un point : lien inutilisable | MINEUR | **corrigé** : découpage par la droite |
| M4 — CSP des pages de la démo : deux empreintes de plus | MINEUR | noté (voir plus haut) |
| M5 — libellé de plus de 80 caractères impossible à confirmer | MINEUR | **corrigé** : 200 |
| M6 — PDF sans limite de concurrence | MINEUR | **non fait** (secrétariat seul) |
| M7 — nombre de désinscriptions exact | MINEUR | **non fait** (pas une personne identifiable : un total) |
| M8 — `List-Unsubscribe` sans désabonnement « en un clic » (RFC 8058) | MINEUR | **non fait** : le jeton est dans le fragment de l'adresse |
| M9 — liens de désinscription invalides après redémarrage si `HACKVS_SECRET` n'est pas fixé | MINEUR | documenté : `HACKVS_SECRET` est obligatoire en production (CONFIGURATION.md) |
| M10 — liens des e-mails dépendant de l'en-tête Host sans `PUBLIC_BASE_URL` | MINEUR | documenté : `PUBLIC_BASE_URL` à fixer en production |
