# Audit final de la mission « Année 1 » — constats et suites

> Sous-agent à contexte neuf, en lecture seule, sur `ec02c68` (annee-1), `origin/foire-2026` et le projet de
> [RAPPORT_ANNEE1.md](RAPPORT_ANNEE1.md). **Aucun BLOQUANT.** Correctifs de code : test ROUGE d'abord
> (`prototype/tests/test_annee1_audit_lot910.py`, tests « final »).

Vérifié **sans rien trouver** :
- **jeton de borne b2** : signature sur nom et échéance, vérifiée avant l'échéance et la révocation ; le journal ne
  garde que le nom ; routes du secrétariat élevé ;
- **langue de « Mon espace »** : espace éteint, `/moi/foire` renvoie exactement la réponse de la démo ;
- **`foire-2026` depuis `d2eaa30`** : 44 fichiers, tous des documents, plus un outil autonome de captures ; aucun
  code produit, aucun test, aucun fichier vidéo ;
- **la phrase finale du pitch** est identique mot pour mot (seules la mise en gras et une didascalie changent) ;
- les deux risques du pitch sont confirmés sur `foire-2026` ;
- « 9 bloquants, tous corrigés » est exact ;
- aucun secret dans le delta ;
- fichiers surveillés par les mutations : 0 changement ;
- aucun test supprimé ni affaibli : 2 fichiers de test existants modifiés, tous deux renforcés ou équivalents.

| Constat | Gravité | Suite |
|---|---|---|
| I-A — révoquer un nom mal tapé (majuscule de tablette, faute) répondait « révoquée » sans effet | IMPORTANT | **corrigé** : la révocation retrouve la borne créée sans tenir compte de la casse ; un nom inconnu est REFUSÉ (rien n'est dit révoqué) ; champ sans majuscule ni correcteur automatiques |
| I-B — liste « non fait » du rapport incomplète ; « Docker de production » sans réserve | IMPORTANT | **corrigé** dans le rapport (exploitation, traçabilité, mineurs ; image non construite) |
| I-C — « démo vérifiée identique après chaque lot » non étayé pour tous les lots ; exceptions voulues non dites | IMPORTANT | **corrigé** : le rapport dit où la trace existe, relance la vérification à la consolidation et nomme les exceptions (JSON-LD des reçus, contraste de `/projection`) |
| M-A — une borne échue affichée « active » | MINEUR | **corrigé** : état « échue » |
| M-B — jeton non ASCII → erreur 500 sur `/borne/passe` (défaut antérieur) | MINEUR | **corrigé** : forme refusée avant toute comparaison (401) |
| M-C — bloquants des audits attribués au mauvais lot dans le rapport | MINEUR | **corrigé** |
| M-D — risque 2 du pitch : « pouvait » au lieu de « peut » ; seul l'API déclenche le retrait | MINEUR | **corrigé** |
| M-E — pas de branche `main` sur le dépôt distant | MINEUR | **dit** dans le rapport : choisir la branche cible avant de fusionner |
| M-F — `foire-2026` contient un outil de captures hors `docs/` | MINEUR | **dit** dans le rapport (inoffensif : ni importé ni testé) |
