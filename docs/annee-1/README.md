# Année 1 — la voie produit (branche `annee-1`)

> Tout ce qui est ici est **construit sur la branche `annee-1` et pas dans la démo du pitch**. Rien n'est « validé sur
> le terrain » : aucun membre réel ne l'a utilisé. La démo du pitch est la branche `foire-2026` (filet : `pitch-stable`).

| Lot | Ce qui est construit | Preuve | Vitrine |
|---|---|---|---|
| 10 · Prototype e-ID | attestations SD-JWT VC des reçus, émetteur et vérificateur locaux — prototype, non connecté à swiyu | `test_annee1_attestations.py` · CLAIMS 114 | [vitrine/lot10.md](vitrine/lot10.md) |
| 11 · Qualité | WCAG 2.2 AA par axe-core dans les E2E ; PWA installable ; file hors ligne des réponses ; charge à 500 et 1 000 membres simulés (budgets tenus après un correctif, premier passage hors budget dit) ; budgets de pages | `test_annee1_accessibilite.py`, `test_annee1_hors_ligne.py`, `test_annee1_budgets.py` · CLAIMS 115-117 | [vitrine/lot11.md](vitrine/lot11.md) |
| 12 · Cohérence visuelle | pages de l'année 1 sur les jetons du Design System, captures avant / après ; pas de refonte (ADR 0010) | `test_annee1_coherence_design.py` · CLAIMS 118 | [vitrine/lot12.md](vitrine/lot12.md) |
| 9 · Allumage Foire | borne de stand, import des exposants, lots de passes, adhésions confirmées | `test_annee1_foire.py` · CLAIMS 113 | [vitrine/lot9.md](vitrine/lot9.md) |
| 8 · Plusieurs clubs, FR/DE/EN | club partenaire exemple fictif, adhésion croisée, membres à distance, interface anglaise | `test_annee1_multiclub.py` · CLAIMS 112 | [vitrine/lot8.md](vitrine/lot8.md) |
| 7 · IA Apertus | suivi du taux d'acceptation (nouveau) ; appel d'outils mesuré, coach SMART, classification, pipeline d'affinage non lancé, parité : faits avant la mission | `test_annee1_suivi_ia.py` · CLAIMS 111 (et 39, 89, 91, 101) | [vitrine/lot7.md](vitrine/lot7.md) |
| 6 · Confiance et conformité | termes DPV vérifiés, journal des accès, HSTS, textes juridiques à valider, ASVS niveau 2 (auto-évaluation) | `test_annee1_confiance.py`, `test_annee1_dpv.py` · CLAIMS 110 | [vitrine/lot6.md](vitrine/lot6.md) · [conformite/](conformite/README.md) |
| 5 · Notifications | e-mail SMTP générique (réel si `SMTP_HOST`, sinon simulé), SMS (interface + faux fournisseur), modèles FR/DE, suivi, désinscription signée ; relance depuis la console | `test_annee1_notifications.py`, `test_annee1_notifications_api.py` · CLAIMS 109 | [vitrine/lot5.md](vitrine/lot5.md) |
| 4 · Console du secrétariat | comptes (inviter, révoquer), métiers à confirmer, critères du pilote gelés d'avance, bilan trimestriel MD / CSV / PDF, campagne d'invitation reliée à « Le Club cherche » ; page `/secretariat` (compte nominatif + TOTP) | `test_annee1_secretariat.py`, `test_annee1_secretariat_api.py` · CLAIMS 108 | [vitrine/lot4.md](vitrine/lot4.md) |
| 3 · Espace membre | mode pause, préférences langue / région / canaux, mes demandes envoyées, solde privé, export de mes données, suppression avec purge réelle du journal ; page `/espace` | `test_annee1_espace_membre.py`, `test_annee1_espace_membre_api.py` · CLAIMS 107 | [vitrine/lot3.md](vitrine/lot3.md) |
| 2 · Authentification et rôles | invitation à usage unique, sessions et appareils, rôles, comptes nominatifs, TOTP pour la console, journal d'administration, CSRF, limite par session ; page `/compte` | `test_annee1_comptes.py`, `test_annee1_comptes_api.py` · CLAIMS 106 | [vitrine/lot2.md](vitrine/lot2.md) |
| 1 · Fondations de production | journal SQLite / PostgreSQL, migrations réversibles, sauvegarde vérifiée, configuration documentée, `/sante/pret`, `/metriques`, Docker de production | `test_annee1_stockage.py`, `test_annee1_exploitation.py` · CLAIMS 104–105 | [vitrine/lot1.md](vitrine/lot1.md) |

Documents : [CONFIGURATION.md](CONFIGURATION.md) · [AUDIT_LOT1.md](AUDIT_LOT1.md) · [AUDIT_LOT23.md](AUDIT_LOT23.md) · [AUDIT_LOT45.md](AUDIT_LOT45.md) · [AUDIT_LOT678.md](AUDIT_LOT678.md) · [AUDIT_LOT910.md](AUDIT_LOT910.md) · [AUDIT_LOT1112.md](AUDIT_LOT1112.md) (constats des audits et suites).

Documents d'affaires (hypothèses, rien d'acquis) : [affaires/README.md](affaires/README.md). Qualité (lot 11) : [qualite/budgets.json](qualite/budgets.json), mesures de charge [500](qualite/charge_500.json) et [1 000](qualite/charge_1000.json) membres simulés.
