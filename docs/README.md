# Documentation — ce qui est à jour, ce qui est historique

Chaque fichier Markdown de `docs/` est classé ci-dessous ; `prototype/tests/test_docs_classees.py` refuse un fichier non
classé, ou un fichier historique sans sa bannière. Un document **à jour** décrit le produit au commit courant ; un document
**daté** est un compte rendu exact à sa date (ses chiffres ne bougent plus) ; un document **historique** décrit un produit
qui n'existe plus.

## À jour

| Fichier | Contenu |
|---|---|
| [/README.md](/README.md) | ce qu'est Club Pulse, comment le lancer et le vérifier, ce qui est réel / synthétique / simulé / non démontré |
| [audit/FINAL_AUDIT.md](audit/FINAL_AUDIT.md) | audit final avant le gel : architecture, sécurité, API, état, tests, performance, claims, limites, risques |
| [audit/CLAIMS.md](audit/CLAIMS.md) | registre des affirmations : chacune prouvée (test), mesurée, démontrable à la main, ou retirée |
| [audit/SENIOR_ENGINEERING_FINDINGS.md](audit/SENIOR_ENGINEERING_FINDINGS.md) | registre des constats F01–F40 et leur état |
| [audit/REVUE_PUBLIQUE.md](audit/REVUE_PUBLIQUE.md) | revue publique R-01 à R-15 |
| [audit/VAGUES_CORRECTIONS.md](audit/VAGUES_CORRECTIONS.md) | chaque correction : test rouge, changement, contre-épreuve, commit |
| [audit/mutants_survivants.txt](audit/mutants_survivants.txt) | survivants de mutation classés équivalents (`capacites.py`) |
| [audit/club-pulse-pivot/DEMO_SCRIPT.md](audit/club-pulse-pivot/DEMO_SCRIPT.md) | script de démonstration, secours, rituel d'avant-scène |
| [presentation/01_CONCEPT.md](presentation/01_CONCEPT.md) · [02_STRUCTURE](presentation/02_STRUCTURE.md) · [03_SCRIPT_ORAL](presentation/03_SCRIPT_ORAL.md) · [03b_SCRIPT_A_DIRE](presentation/03b_SCRIPT_A_DIRE.md) · [04_DEMO_RUNBOOK](presentation/04_DEMO_RUNBOOK.md) · [05_FILM_INTEGRATION](presentation/05_FILM_INTEGRATION.md) · [06_SLIDE_CONTENT](presentation/06_SLIDE_CONTENT.md) · [07_QA_JURY](presentation/07_QA_JURY.md) · **[COMMENT_PRESENTER](presentation/COMMENT_PRESENTER.md)** (guide pas à pas, Mac) · [18 ou 15 min](presentation/08_VERSIONS_18_15.md) · [répétitions](presentation/09_REPETITIONS.md) · [questions du jury, complet](presentation/07_QA_JURY_COMPLET.md) · [top 20](presentation/qa/TOP20.md) · [visite guidée](presentation/VISITE_GUIDEE.md) · **v2 (18 min)** : [02_STRUCTURE_v2](presentation/02_STRUCTURE_v2.md) · [03_SCRIPT_ORAL_v2](presentation/03_SCRIPT_ORAL_v2.md) · [03b_SCRIPT_A_DIRE_v2](presentation/03b_SCRIPT_A_DIRE_v2.md) · [04_DEMO_RUNBOOK_v2](presentation/04_DEMO_RUNBOOK_v2.md) · [06_SLIDE_CONTENT_v2](presentation/06_SLIDE_CONTENT_v2.md) · [motion](presentation/motion/README.md) · [deck](presentation/deck/README.md) · [deck — direction](presentation/deck/DIRECTION.md) · [état du 02.10 soir](presentation/ETAT_02_10_SOIR.md) · [livrables](presentation/livrables/README.md) · [outils](presentation/outils/README.md) | présentation finale (10 min) : concept carte → reçu, neuf actes, script oral, runbook de démo adossé à DEMO_SCRIPT, film, contenu des slides, questions du jury, motion design qui remplace le deck (lecteur de scène + rendu MP4), deck motion clair (direction, revue PNG, gel.json) |
| [audit/club-pulse-pivot/PREUVES.md](audit/club-pulse-pivot/PREUVES.md) | commandes exécutées et résultats (chiffres finaux figés au gel) |
| [roadmap/README.md](roadmap/README.md) · [ROADMAP](roadmap/ROADMAP.md) · [SUIVI_METRIQUES](roadmap/SUIVI_METRIQUES.md) · [FINANCEMENT_JURIDIQUE](roadmap/FINANCEMENT_JURIDIQUE.md) · [BENCHMARK](roadmap/BENCHMARK.md) · [APERTUS_PLAN](roadmap/APERTUS_PLAN.md) · [ARCHITECTURE_SWIYU_VOIX_MINI](roadmap/ARCHITECTURE_SWIYU_VOIX_MINI.md) | feuille de route six mois, tableau d'avancement daté, métriques de Suivi, financement et cadre juridique, benchmark, plan Apertus |
| [bilans/bilan-demo.md](bilans/bilan-demo.md) · [bilan-7j](bilans/bilan-7j.md) · [bilan-trimestre](bilans/bilan-trimestre.md) | bilans de période générés par `make bilan` (monde de démonstration, scène Foire 2026 jouée par le script) : mêmes chiffres que Suivi |
| [RAPPORT_NUIT.md](RAPPORT_NUIT.md) | rapport de la nuit Foire 2026 : fait / non fait, chiffres mesurés, simulé, risques, rituel de 08:00 |
| [NUIT.md](NUIT.md) | nuit du 3 au 4 octobre (« Foire 2026 ») : plan horaire, statut heure par heure |
| [THREAT_MODEL.md](THREAT_MODEL.md) | modèle de menaces |
| [design/DESIGN_SYSTEM.md](design/DESIGN_SYSTEM.md) | design system v1.0 et écarts assumés |
| [ADR/README.md](ADR/README.md) | décisions d'architecture et leur statut relu contre le code |
| [audit/EXTRACTION_EVAL.md](audit/EXTRACTION_EVAL.md) · [audit/probe_publicai.md](audit/probe_publicai.md) (sonde exécutée contre le CSCS) | évaluation EXTRACT (prête, non exécutée contre un vrai modèle) ; sonde du fournisseur |
| [BANC_MULTI_FOURNISSEURS.md](BANC_MULTI_FOURNISSEURS.md) | banc IA Apertus / OpenAI / Claude sur les 26 mêmes cas : choix du fournisseur, variables, commandes, dry-run, rapport, limites |
| [roadmap/financement/INTERREG_PRE_PROJET.md](roadmap/financement/INTERREG_PRE_PROJET.md) · [INNOSUISSE_NOTE.md](roadmap/financement/INNOSUISSE_NOTE.md) | dossiers de financement (brouillons) : partenaires tous « à contacter », conditions à revérifier |
| [audit/AUDIT_NUIT.md](audit/AUDIT_NUIT.md) | audit de nuit par un sous-agent à contexte neuf (sur `e2b1745`) : 1 BLOQUANT, 8 IMPORTANT, 12 MINEUR ; réponses point par point dans RAPPORT_NUIT.md |
| [conformite/REGISTRE_TRAITEMENTS.md](conformite/REGISTRE_TRAITEMENTS.md) | modèle de registre des traitements (nLPD / RGPD), **à valider par un juriste** ; page d'information FR / DE : `/confidentialite` |
| [conformite/RECU_27560.md](conformite/RECU_27560.md) | reçus alignés sur ISO/IEC TS 27560 (jamais « certifiés ») : table de correspondance, export JSON-LD DPV, test de conformité, limites |
| [DEMO_TUNNEL.md](DEMO_TUNNEL.md) | **démo publique sur le Mac du pitch** : lanceur, Tailscale Funnel (principal), Cloudflare (secours), vérifications, ce qu'on dit |
| [DEPLOIEMENT.md](DEPLOIEMENT.md) | production future : déploiement VPS Infomaniak (Docker Compose + Caddy, HTTPS) pas à pas |
| [DEPLOIEMENT_CLOUD_RUN.md](DEPLOIEMENT_CLOUD_RUN.md) | déploiement public Cloud Run : commandes exactes, variables, secrets, contrôles (rien n'est déployé) |
| [audit/latence_apertus.md](audit/latence_apertus.md) | latence réelle d'Apertus (n appels, médiane, p95), mesure séparée de la démonstration |

| [annee-1/CONFIGURATION.md](annee-1/CONFIGURATION.md) · [annee-1/README.md](annee-1/README.md) · [vitrine lot 1](annee-1/vitrine/lot1.md) | **Année 1 — branche `annee-1`, pas dans la démo** : configuration complète (variables d'environnement), vitrine des lots |

## Daté (exact à sa date, non mis à jour)

| Fichier | Date |
|---|---|
| [audit/SENIOR_ENGINEERING_AUDIT.md](audit/SENIOR_ENGINEERING_AUDIT.md) | audit profond, 01.10 (commit `53e87cd`) |
| [audit/PHASE_1.md](audit/PHASE_1.md) · [PHASE_2](audit/PHASE_2.md) · [PHASE_3](audit/PHASE_3.md) | comptes rendus de phase, 30.09 |
| [audit/PIVOT_INSPECTION.md](audit/PIVOT_INSPECTION.md) | inspection avant le registre des capacités, 30.09 |
| [audit/club-pulse-pivot/ACCEPTANCE_MATRIX.md](audit/club-pulse-pivot/ACCEPTANCE_MATRIX.md) · [HANDOFF_FOR_CODEX](audit/club-pulse-pivot/HANDOFF_FOR_CODEX.md) · [REVUE_JURY](audit/club-pulse-pivot/REVUE_JURY.md) · [ETAT_INITIAL](audit/club-pulse-pivot/ETAT_INITIAL.md) | tranche « action collective », 29–30.09 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | **partiellement périmé** (constat F02) : pivot du 29.09, avant le registre des capacités |
| ADR 0001–0008 (voir [ADR/README.md](ADR/README.md)) | 29.09 ; 0004 remplacée |

## Historique (produit d'avant le pivot — bannière en tête de chaque fichier)

[ANCIEN_PROTOTYPE.md](ANCIEN_PROTOTYPE.md) · [ARCHITECTURE_FIL_DU_CLUB.md](ARCHITECTURE_FIL_DU_CLUB.md) ·
[ASSUMPTIONS.md](ASSUMPTIONS.md) · [AUDIT_PACKET.md](AUDIT_PACKET.md) · [CURRENT_STATE.md](CURRENT_STATE.md) ·
[DECISIONS.md](DECISIONS.md) · [DEMO.md](DEMO.md) · [DEPLOIEMENT_ANCIEN.md](DEPLOIEMENT_ANCIEN.md) · [EVALUATION.md](EVALUATION.md) ·
[HANDOFF.md](HANDOFF.md) · [LEARNING.md](LEARNING.md) · [LIMITATIONS.md](LIMITATIONS.md) · [LOOPS.md](LOOPS.md) ·
[OPEN_SOURCE_RECON.md](OPEN_SOURCE_RECON.md) · [REPRISE.md](REPRISE.md) · [RESEARCH.md](RESEARCH.md) ·
[SENIOR_CODE_REVIEW.md](SENIOR_CODE_REVIEW.md) · [STRATEGIC_RESEARCH.md](STRATEGIC_RESEARCH.md) ·
[TARGET_ARCHITECTURE.md](TARGET_ARCHITECTURE.md) · [architecture/RECOMPOSITION.md](architecture/RECOMPOSITION.md)

Le dossier `/competition/` (pitch de l'ancien produit) est en quarantaine : bannière « OBSOLÈTE — ne pas présenter » sur
chaque fichier, vérifiée par `prototype/tests/test_quarantaine_competition.py`. Les limites ACTUELLES du produit sont
dans `audit/FINAL_AUDIT.md` § 12, pas dans l'ancien `LIMITATIONS.md`.
