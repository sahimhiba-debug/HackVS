# Année 1 — la voie produit (branche `annee-1`)

> Tout ce qui est ici est **construit sur la branche `annee-1` et pas dans la démo du pitch**. Rien n'est « validé sur
> le terrain » : aucun membre réel ne l'a utilisé. La démo du pitch est la branche `foire-2026` (filet : `pitch-stable`).

| Lot | Ce qui est construit | Preuve | Vitrine |
|---|---|---|---|
| 3 · Espace membre | mode pause, préférences langue / région / canaux, mes demandes envoyées, solde privé, export de mes données, suppression avec purge réelle du journal ; page `/espace` | `test_annee1_espace_membre.py`, `test_annee1_espace_membre_api.py` · CLAIMS 107 | [vitrine/lot3.md](vitrine/lot3.md) |
| 2 · Authentification et rôles | invitation à usage unique, sessions et appareils, rôles, comptes nominatifs, TOTP pour la console, journal d'administration, CSRF, limite par session ; page `/compte` | `test_annee1_comptes.py`, `test_annee1_comptes_api.py` · CLAIMS 106 | [vitrine/lot2.md](vitrine/lot2.md) |
| 1 · Fondations de production | journal SQLite / PostgreSQL, migrations réversibles, sauvegarde vérifiée, configuration documentée, `/sante/pret`, `/metriques`, Docker de production | `test_annee1_stockage.py`, `test_annee1_exploitation.py` · CLAIMS 104–105 | [vitrine/lot1.md](vitrine/lot1.md) |

Documents : [CONFIGURATION.md](CONFIGURATION.md) · [AUDIT_LOT1.md](AUDIT_LOT1.md) (constats de l'audit du lot 1 et suites).
