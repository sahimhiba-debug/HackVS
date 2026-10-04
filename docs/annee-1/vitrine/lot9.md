# Lot 9 — Allumage Foire

> **Construit — branche `annee-1`, pas dans la démo.** Interrupteur `HACKVS_FOIRE_ALLUMAGE=1` (éteint par défaut).
> Monde FICTIF ; aucune adhésion réelle n'a été mesurée.

![La borne du stand, après qu'un visiteur a pris son passe : QR et référence](lot9-borne.png)

| Demandé par la mission | Où | Preuve |
|---|---|---|
| Mode stand (borne) | page `/borne`, ouverte une fois par un lien du secrétariat (jeton signé gardé par la borne) ; un visiteur à la fois (3 s), 500 passes par jour et par borne ; le QR disparaît après 45 s | `test_la_borne_exige_son_jeton_et_respecte_son_rythme`, `test_la_borne_dans_un_vrai_navigateur` |
| Import d'une liste d'exposants en CSV | console : « Importer les exposants » (exposant ; métier ; stand) → un passe par exposant, dédoublonné ; le fichier rendu (lien + référence) n'est PAS gardé | `test_import_des_exposants_dedoublonne_et_ne_garde_aucun_nom` |
| Passe découverte à grande échelle | lots de 500 au plus, tout ou rien (500 passes en moins de 20 s dans le test) | `test_passes_a_grande_echelle` |
| Mesure des adhésions venues du passe | entonnoir par origine : émis → activés → ont aidé → intentions → **adhésions confirmées par le secrétariat** (avec la référence que l'invité montre) ; « < 3 » en entreprises ; taux = adhésions / passes émis | `test_entonnoir_adhesions_confirmees_jamais_des_intentions`, `test_sous_trois_entreprises_…` |

**Limites.** La référence s'affiche sur la borne et dans le fichier des exposants ; l'écran du passe découverte (la page
de la démo) ne la montre pas encore. Le rythme de la borne est gardé en mémoire (un redémarrage le remet à zéro).

**Après l'audit des lots 9-10** ([AUDIT_LOT910.md](../AUDIT_LOT910.md)) : la console ne reçoit plus la liste des
intentions (le secrétariat saisit la référence que l'invité montre) ; un invité qui a retiré son consentement n'est
plus compté ni confirmable ; les cellules du fichier rendu qui ressembleraient à une formule de tableur sont
neutralisées ; le plafond de la borne suit le jour réel. Non fait : un jeton de borne n'expire pas et ne se révoque
pas (seul recours : changer le secret du serveur).
