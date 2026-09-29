# Dossier de compétition — Hack VS 2026 (préparé AVANT l'événement)

Tout ce dossier raconte la même histoire que le code. Garde-fous :
- `prototype/scripts/validate_competition_claims.py` : exécute les contrôles du registre des preuves, vérifie que tout
  chiffre du pitch est prouvé, que les routes de la démo existent et que la vidéo correspond aux légendes ;
- `prototype/scripts/generer_competition.py` : régénère les documents vidéo et le minutage depuis leurs sources ;
- `prototype/scripts/enregistrer_video.py` : réenregistre la vidéo depuis la vraie scène.

Commencer par : PITCH_3MIN → 09_DEMO_SCRIPT → 14_PROOF_LEDGER → FAILURES → 13_QA_JURY → ANNEXE_TECHNIQUE.
Données : fictives ou synthétiques, étiquetées ; aucune donnée du Club.

## Correspondance avec la liste du mandat
| Attendu | Fichier |
|---|---|
| PRODUCT_THESIS · PROBLEM · SOLUTION | 01_PRODUCT_THESIS · 02_PROBLEM · 03_SOLUTION |
| ARCHITECTURE · ARCHITECTURE_DECISIONS | 04_ARCHITECTURE · ANNEXE_TECHNIQUE · ARCHITECTURE_DECISIONS |
| DIFFERENTIATION · COMPETITIVE_ANALYSIS | 05_DIFFERENTIATION · 20_COMPETITIVE_ANALYSIS · AUDIT_CHAMPIONNAT (matrice sourcée) |
| BENCHMARKS · METRICS | 06_BENCHMARKS (SYNTHETIC_BENCHMARK) · 07_METRICS |
| PRIVACY · FAILURES | 08_PRIVACY · FAILURES (47, avec index par thème) |
| PROOF_LEDGER | 14_PROOF_LEDGER (généré) · claims.json (source) · 15_CLAIMS |
| PITCH | PITCH_90SEC · PITCH_3MIN · PITCH_5MIN · 10_PITCH (récit, deck, temps) · deck `/presentation` |
| VIDEO_SCRIPT · VIDEO_STORYBOARD | video/VIDEO_SCRIPT (généré) · 12_VIDEO_STORYBOARD · video/captions.json (source) |
| QA_JURY | 13_QA_JURY (45 questions : réponse, preuve, limite) · OBJECTIONS |
| LIMITATIONS · ROADMAP | 16_LIMITATIONS · 17_ROADMAP |
| DEMO_SCRIPT · LIVE_DEMO_CHECKLIST | 09_DEMO_SCRIPT · 18_LIVE_DEMO_CHECKLIST · rehearsal/ |
| RESEARCH_LOG | RESEARCH_LOG · EXPERIMENT_LOG · GENAI_RESEARCH |
| Valeur métier | VALEUR_METIER |

