# Audit des lots 6 (confiance), 7 (suivi IA) et 8 (plusieurs clubs) — constats et suites

> **Construit — branche `annee-1`, pas dans la démo.** Audit d'un sous-agent à contexte neuf, en lecture seule, sur
> `c735f84`. Chaque constat corrigé a d'abord un test ROUGE (`prototype/tests/test_annee1_audit_lot678.py`), puis vert.

Vérifié **sans rien trouver** : chaque terme DPV existe (liste identique aux 1 128 termes officiels) ; le CSV ASVS est
identique au fichier officiel ; tous les chiffres du lot 7 sont dans leurs fichiers de preuve (sauf « 1,5 s », retiré) ;
un membre ne peut ni déclarer un club ni voir qui est dans un autre ; aucune régression du français ni de l'allemand ;
**démo inchangée** (66 faits, mêmes empreintes du journal et de l'état, 24 demandes, 17 découvertes).

| Constat | Gravité | Suite |
|---|---|---|
| B1 — la purge d'un membre réécrivait le journal des ACCÈS (route, « qui ») et le nom d'un club exemple | BLOQUANT | **corrigé** : les faits de sécurité et de gouvernance (accès, comptes, sessions, second facteur, administration, clubs déclarés, notifications, purge, critères, campagnes…) ne sont jamais réécrits ; `route`, `etiquette`, `action`, `cible`, `par` protégés |
| I1 — suivi IA : le seuil des acceptations se comptait sur ceux qui avaient PROPOSÉ | IMPORTANT | **corrigé** : seuil sur ceux qui ont accepté ; taux non dit si acceptants ou non-acceptants viennent de moins de 3 entreprises |
| I2 — le journal des accès ne couvrait ni les refus ni l'administration | IMPORTANT | **corrigé** : refus d'une session valide tracés (« (refusé) »), routes `/comptes/admin/*` tracées. La console de DÉMONSTRATION (jeton partagé) n'est pas tracée : c'est dit (écrire dans le journal de la démo changerait la démo) |
| I3 — 8 statuts ASVS « conforme » surévalués | IMPORTANT | **corrigé** : passés « partiel » avec la raison (30 conformes, 21 partiels) |
| I4 — l'anglais était actif sans l'interrupteur | IMPORTANT | **corrigé** : `/api/pulse/langues` n'existe que si `HACKVS_MULTICLUB=1` ; sinon le téléphone reste en français ; la phrase ajoutée au dictionnaire allemand est retirée (la démo allemande ne change pas) |
| I5 — choisir « English » dans « Mon espace » n'avait aucun effet | IMPORTANT | **corrigé ensuite** (même nuit, test rouge d'abord : `test_annee1_langue_espace.py`) : la langue choisie voyage dans la réponse de `/moi/foire`, que le téléphone lit déjà — aucune requête de plus ; espace éteint, réponse identique à la démo. Premier essai (un appel de plus, erreur dans la console de la démo) retiré |
| I6 — un membre effacé comptait encore dans les clubs ; l'export ne disait pas ses clubs | IMPORTANT | **corrigé** : décomptes sur les membres présents ; export avec les clubs et « à distance » |
| M1 — chaque consultation écrit un fait (journal qui grossit) ; rétention de 12 mois non appliquée | MINEUR | **non fait**, noté |
| M2 — « fictif » contrôlé par une sous-chaîne | MINEUR | **corrigé** : le nom se termine par « exemple fictif » |
| M3 — l'anglais ne couvre que le dictionnaire (~55 libellés) | MINEUR | vitrine corrigée : dit tel quel |
| M4 — politique : « décomptes seulement » (le secrétariat voit aussi la liste des comptes) ; sauvegardes « chiffrées » dans le contrat | MINEUR | **corrigé** dans les textes |
| M5 — HSTS avec `includeSubDomains` figé | MINEUR | **corrigé** : sans `includeSubDomains` |
| M6 — « 1,5 s » sans preuve conservée | MINEUR | **retiré** |
| M7 — l'export JSON-LD des reçus change aussi dans la démo de cette branche | MINEUR | voulu (termes corrigés) ; dit dans la vitrine du lot 6 |
| Juridique — « membres frontaliers » au lieu de RGPD art. 3 al. 2 | MINEUR | **corrigé** (« à évaluer ») ; les articles de la nLPD n'ont pas pu être vérifiés en ligne (fedlex bloqué) |
