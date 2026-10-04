# Audit des lots 9 (allumage Foire) et 10 (prototype e-ID) — constats et suites

> **Construit — branche `annee-1`, pas dans la démo.** Audit d'un sous-agent à contexte neuf, en lecture seule, sur
> `9d9213a`. Chaque constat corrigé a d'abord un test ROUGE (`prototype/tests/test_annee1_audit_lot910.py`), puis vert.

Vérifié **sans rien trouver** :
- interrupteurs éteints : les 10 routes nouvelles répondent 404, et aucune trace d'accès n'est écrite ;
- autorisations du secrétariat (rôle, double authentification, session élevée) ;
- jeton de borne : HMAC comparé à temps constant ;
- lots tout ou rien ;
- journal de l'import réduit à des décomptes ;
- signature ES256 et empreintes SHA-256 conformes ;
- falsifications refusées ;
- aucun identifiant du membre dans l'attestation ;
- pages construites par `textContent` sous CSP stricte ;
- mention « prototype, non connecté à swiyu » partout.

**Démo inchangée** (66 faits, mêmes empreintes du journal et de l'état, 17 découvertes).

| Constat | Gravité | Suite |
|---|---|---|
| B1 — le vérificateur acceptait n'importe quel émetteur `did:jwk` (une clé inventée signait une « attestation valide ») ; une divulgation nommée `iss` ou `vct` écrasait l'affirmation signée ; une divulgation répétée était acceptée | BLOQUANT | **corrigé** : l'émetteur attendu est un paramètre OBLIGATOIRE ; la route publique ne reconnaît que l'émetteur de CE serveur ; noms réservés (`iss`, `vct`, `iat`, `nbf`, `exp`, `cnf`, `status`, `sub`, `_sd`, `_sd_alg`, `...`) refusés dans une divulgation ; divulgation répétée et nom répété refusés |
| I1 — cinq entrées malformées faisaient une erreur 500 sur la route publique | IMPORTANT | **corrigé** : types vérifiés (en-tête et corps objets, dates entières, divulgation à 3 éléments avec un nom texte) ; toute entrée illisible est refusée proprement |
| I2 — la console recevait la liste des intentions avec métier et région par ligne (contournait le « < 3 » de l'entonnoir) ; un invité qui avait retiré son consentement restait listé et confirmable (le retrait était appliqué AVANT la déclaration, qui la recréait) | IMPORTANT | **corrigé** : la console ne reçoit plus que l'entonnoir ; le secrétariat SAISIT la référence que l'invité montre ; le retrait est appliqué en dernier ; un passe retiré n'est ni compté en intention ni confirmable. Ce défaut d'ordre existe aussi dans `decouverte.py` sur `foire-2026` (la démo n'a aucun retrait d'invité) : **non porté** sur la voie pitch, dit dans le rapport |
| I3 — formules de tableur recopiées dans le CSV rendu des exposants | IMPORTANT | **corrigé** : une cellule qui commence par `=`, `+`, `-`, `@`, une tabulation ou un retour est préfixée d'une apostrophe. La même remarque vaut pour `intelligence/bilan.py` (hors de ces lots) : **non fait**, noté |
| I4 — `exp` = émission + 365 jours, sans lien avec la fin de l'accord ; un état « pièce disparue » signé « echu » | IMPORTANT | **corrigé** : `exp` ≤ fin du jour « jusqu'au » de l'accord ; statut « valable » seulement si le reçu l'est, sinon « retire » ou « invalide ». Limite dite : la fin de l'accord est en date SIMULÉE du Club, `exp` en heure réelle — dans un monde de démonstration avancé dans le temps, les deux peuvent diverger |
| M1 — jeton de borne sans échéance ni révocation | MINEUR | **corrigé ensuite** (même nuit, test rouge d'abord) : jeton « b2 » avec échéance signée (14 jours), révocation par le secrétariat (journal : le nom de la borne seul), liste des bornes dans la console ; l'ancien format sans échéance est refusé |
| M2 — plafond journalier de la borne lié à la date simulée ; compté même si l'émission échouait | MINEUR | **corrigé** : jour réel de l'horloge ; compté après l'émission |
| M3 — plafond Pydantic de l'import (200 000) au-dessus du plafond du corps (64 Kio) | MINEUR | **corrigé** : 60 000 |
| M4 — le nombre d'empreintes `_sd` révèle combien d'affirmations existent | MINEUR | **non fait** (pas d'empreintes leurres, facultatives dans la RFC 9901) ; dit dans la vitrine du lot 10 |
