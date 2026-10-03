# Lot 3 — L'espace membre

> **Construit — branche `annee-1`, pas dans la démo.** Interrupteur `HACKVS_ESPACE_MEMBRE=1` (éteint par défaut).
> Capture réelle d'un membre FICTIF du monde de démonstration : `python prototype/scripts/capturer_vitrine_annee1.py`.

![Mon espace : pause posée, préférences, solde privé, mes demandes, mes données, suppression](lot3-espace-membre.png)

| Demandé par la mission | Où | Preuve |
|---|---|---|
| Premier lancement guidé, déclarer ce qu'on offre | existait (accueil de l'application membre) | tests existants de l'accueil |
| Mes demandes envoyées | `/moi/espace` → `demandes` | `test_mes_demandes_envoyees` |
| Historique des reçus, clôture | existait (reçus ISO/IEC TS 27560, clôture de l'essai) | tests existants |
| Préférences langue / région / canaux | `/moi/preferences` | `test_preferences_langue_region_canaux` |
| MODE PAUSE | `/moi/pause`, `/moi/pause/fin` ; `ClubPulse._membre_peut` | `test_mode_pause_on_ne_recoit_plus_rien_jusqu_a_la_date`, `test_la_pause_survit_a_un_redemarrage` |
| Solde privé « reçus / donnés » | `/moi/espace` → `solde` (visible par le membre seul) | `test_pause_preferences_et_espace` |
| Export de mes données | `/moi/export` (fichier JSON) | `test_export_de_mes_donnees_et_rien_d_autre`, `test_export_telechargeable` |
| Suppression du compte avec purge réelle | `/moi/effacer-definitivement` (confirmation exigée) | `test_purge_reelle_…`, `test_apres_purge_…`, `test_reecrire_est_tout_ou_rien` (SQLite + PostgreSQL) |

**Ce que la purge fait vraiment** (refaite après l'audit des lots 2-3, voir [AUDIT_LOT23.md](../AUDIT_LOT23.md)). Chaque
texte écrit par le membre, son nom, son courriel et son téléphone sont remplacés par « [effacé] » PARTOUT dans le
journal, y compris là où ils ont été recopiés (adaptations, protocoles, accords d'autres membres). Dates, heures et
identifiants ne sont jamais touchés. Le monde purgé est rejoué et relu dans une copie AVANT toute écriture ; puis la
réécriture est tout ou rien, et une trace `PURGE` unique, sans contenu, est ajoutée. Sur le disque : SQLite en
`secure_delete`, PostgreSQL `VACUUM FULL`.

**Limites connues.** Un texte d'un seul mot en minuscules ressemble à un identifiant et peut rester. Les sauvegardes
faites AVANT la purge, et le WAL de PostgreSQL, gardent les textes le temps de leur rétention (à fixer au lot 6).
