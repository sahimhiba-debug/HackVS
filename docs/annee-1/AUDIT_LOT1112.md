# Audit des lots 11 (qualité), 12 (cohérence visuelle) et des documents d'affaires — constats et suites

> **Construit — branche `annee-1`, pas dans la démo.** Audit d'un sous-agent à contexte neuf, en lecture seule, sur
> `c1bd33e`, `07f0033`, `5b76f14`, `8bd89c2` et l'arbre de travail. **Aucun BLOQUANT.** Les correctifs de code ont
> d'abord un test ROUGE (`prototype/tests/test_annee1_hors_ligne.py`, `test_annee1_charge_lectures.py`).

Vérifié **sans rien trouver** :
- file hors ligne : jamais envoyée sous un autre compte, pas de double envoi, serveur seul juge, pas d'injection de
  code, interrupteur éteint sans effet ;
- index gardé : la version du journal change à chaque écriture, annulation, purge ou vidage, y compris par un autre
  objet sur le même fichier ;
- chiffres de charge identiques aux fichiers de mesure ;
- contre-preuve d'accessibilité réelle et portée honnête ;
- faits externes des documents d'affaires recoupés (Interreg France-Suisse et Italia-Svizzera, chèque Innosuisse,
  Mondiaux de Crans-Montana, Foire du Valais) ;
- aucun partenaire présenté comme acquis ;
- jetons du lot 12 tous définis, contrastes AA tenus ;
- fichiers surveillés par les mutations intacts, aucun test affaibli.

| Constat | Gravité | Suite |
|---|---|---|
| I1 — la file hors ligne gardait le JETON de session et survivait à « Se déconnecter » et « Tout effacer » | IMPORTANT | **corrigé** : la file garde l'identifiant du membre, jamais le jeton ; vidée par « Se déconnecter » et « Tout effacer » ; la réponse d'un autre membre trouvée sur l'appareil est effacée, jamais envoyée, et c'est dit |
| I2 — une réponse gardée était perdue sans bruit si l'application était fermée puis rouverte (nouveau jeton) | IMPORTANT | **corrigé** : liée au membre, elle part après la reconnexion (test « fermer, rouvrir, se reconnecter ») |
| I3 — le stockage local des réponses n'était dit nulle part ; ASVS V8.2.2 devenu faux | IMPORTANT | **corrigé** : politique FR / DE, kits d'accueil, ASVS V8.2.2 régénéré |
| I4 — budgets de charge déclarés tenus sur une charge presque sans écriture | IMPORTANT | **corrigé** : une écriture par membre dans le script ; budgets toujours tenus, **de justesse** pour les lectures ; dit dans la vitrine et CLAIMS 117 |
| I5 — kits et guide citaient des libellés absents de l'interface (allemand non traduit, « Exporter », « Pause », « Campagnes », « IA », bilan HTML) | IMPORTANT | **corrigé** : libellés réels cités ; en allemand, les boutons non traduits sont cités en français et dits tels |
| M1 — « < 3 » employé comme tranche de prix comptée en membres | MINEUR | **corrigé** : compté en entreprises |
| M2 — la liste gardée de l'index était partagée et modifiable | MINEUR | **corrigé** : une copie est rendue (test) |
| M3 — attente fixe avant axe | MINEUR | **corrigé** : attente de la fin des lectures réseau |
| M4 — « tout allumé » n'allumait pas la file hors ligne | MINEUR | **corrigé** |
| M5 — résultats « incomplete » d'axe non comptés | MINEUR | **non fait**, la portée de CLAIMS 115 (violations) reste exacte |
| M6 — budgets de pages mesurés sans session | MINEUR | **non fait**, noté |
| M7 — mesures du premier passage écrasées ; profil non conservé ; coquille | MINEUR | **corrigé** : `qualite/charge_*_passage1.json` restaurés de l'historique ; profil dit « non conservé » ; coquille corrigée |
| M8 — interrupteur éteint : un `removeItem` par écran, écouteur `online` toujours posé | MINEUR | **non fait** (aucun effet visible, démo identique) |
| M9 — lot 12 : capture `compte` identique, filets plus pâles, `rgb()` non contrôlé | MINEUR | **corrigé** dans la vitrine |
| M10 — note Innosuisse : délai de 6 mois, éligibilité possible de l'association | MINEUR | **corrigé** (« à confirmer ») |

**Trouvé par la suite complète après ces correctifs** (pas par l'audit) : deux tests de cette nuit étaient fragiles sous
charge. (1) Le budget des pages comptait les octets par `response.body()`, qui échoue en silence sous charge (`/app`
compté 36 Ko au lieu de 123 Ko) : une mesure qui pouvait CACHER un dépassement. Remplacée par l'API Performance du
navigateur (`decodedBodySize`), mêmes budgets, même contre-preuve. (2) Le test « interrupteur éteint » attendait un
seul toast « Hors ligne » alors que deux peuvent s'afficher (coupure + action) : il attend le premier. Aucune assertion
retirée.
